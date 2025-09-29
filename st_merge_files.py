import streamlit as st
import pandas as pd
import re


def main():
    st.title("📊 Объединение таблиц эксперимента")
    st.write("Загрузите три таблицы и введите параметры эксперимента")

    # Секция для ввода общих параметров эксперимента
    st.header("Параметры эксперимента")

    col1, col2 = st.columns(2)
    with col1:
        exposure_time = st.text_input("Exposure time", value="")
        compound = st.text_input("Compound", value="")
    with col2:
        st.write("Test/Control определяется автоматически:")
        st.write("A* = Control, B*-F* = Test")

    # Ввод концентраций для разных well_id
    st.subheader("Концентрации для ячеек")
    st.write("Для контрольной группы (A*) концентрация не указывается")

    concentrations = {}
    well_letters = ['B', 'C', 'D', 'E', 'F']

    cols = st.columns(5)
    for i, well in enumerate(well_letters):
        with cols[i]:
            concentrations[well] = st.text_input(f"Концентрация {well}*", value="", key=f"conc_{well}")

    # Загрузка трех таблиц
    st.header("Загрузка таблиц")

    uploaded_files = st.file_uploader(
        "Загрузите три Excel таблицы",
        type=['xlsx', 'xls'],
        accept_multiple_files=True,
        key="main_uploader"
    )

    dfs = []
    if uploaded_files and len(uploaded_files) == 3:
        for i, uploaded_file in enumerate(uploaded_files):
            df = load_excel_file(uploaded_file, f"Таблица {i + 1}")
            if df is not None:
                dfs.append(df)

    # Кнопка для объединения таблиц
    if dfs and len(dfs) == 3:
        if st.button("Объединить таблицы"):
            try:
                # Проверяем, что все обязательные параметры заполнены
                if not all([exposure_time, compound]):
                    st.warning("Пожалуйста, заполните все обязательные параметры эксперимента")
                    return

                # Проверяем концентрации для тестовых групп
                missing_concentrations = [well for well in well_letters if not concentrations[well]]
                if missing_concentrations:
                    st.warning(f"Пожалуйста, укажите концентрации для ячеек: {', '.join(missing_concentrations)}")
                    return

                # Объединяем таблицы
                result_df = merge_tables_corrected(dfs[0], dfs[1], dfs[2], exposure_time, compound, concentrations)

                if result_df.empty:
                    st.error("Не удалось создать результирующую таблицу.")
                    return

                # Добавляем статичные строки с названиями столбцов
                result_df_with_headers = add_column_headers(result_df)

                st.success("✅ Таблицы успешно объединены!")

                # Показываем результат
                st.header("Результирующая таблица")
                st.dataframe(result_df_with_headers)

                # Статистика
                st.subheader("📈 Статистика")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Всего строк", len(result_df_with_headers))
                with col2:
                    # Исключаем строки заголовков из подсчета experiment_id (первые 4 строки)
                    data_rows = result_df_with_headers.iloc[
                                4:]  # Пропускаем первые 4 строки (1 основной заголовок + 3 дополнительных)
                    st.metric("Уникальные experiment_id", data_rows['experiment_id'].nunique())
                with col3:
                    st.metric("Уникальные well_id", data_rows['well_id'].nunique())

                st.write(f"Well_id в данных: {sorted(data_rows['well_id'].unique())[:10]}...")

                # Скачивание результата
                csv = result_df_with_headers.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="📥 Скачать объединенную таблицу как CSV",
                    data=csv,
                    file_name="merged_experiment_data.csv",
                    mime="text/csv"
                )

            except Exception as e:
                st.error(f"❌ Ошибка при объединении таблиц: {e}")
                st.exception(e)


def load_excel_file(uploaded_file, table_name):
    """Загрузка Excel файла"""
    try:
        df = pd.read_excel(uploaded_file, header=None)
        st.write(f"**{table_name}:** {df.shape[1]} столбцов, {df.shape[0]} строк")
        return df
    except Exception as e:
        st.error(f"Ошибка при чтении файла {table_name}: {e}")
        return None


def parse_time_interval(time_str):
    """Парсит временной интервал и возвращает среднее время в минутах"""
    try:
        if isinstance(time_str, str):
            times = re.findall(r'(\d+):(\d+):(\d+)', time_str)
            if len(times) >= 2:
                start_h, start_m, start_s = map(int, times[0])
                end_h, end_m, end_s = map(int, times[1])
                start_total_minutes = start_h * 60 + start_m + start_s / 60
                end_total_minutes = end_h * 60 + end_m + end_s / 60
                return (start_total_minutes + end_total_minutes) / 2
        return 0
    except:
        return 0


def calculate_light_status(time_minutes):
    """Определяет статус света - каждые 10 минут переключение, начинается с Off"""
    cycle_position = time_minutes % 20
    return "Off" if cycle_position < 10 else "On"


def extract_well_letter(well_id):
    """Извлекает букву из well_id (A3 -> A, B4 -> B)"""
    try:
        well_str = str(well_id).strip()
        match = re.search(r'^([A-Za-z])', well_str)
        if match:
            return match.group(1).upper()
        return ""
    except:
        return ""


def get_test_control(well_id):
    """Определяет Test/Control по well_id"""
    well_letter = extract_well_letter(well_id)
    return "Control" if well_letter == 'A' else "Test"


def get_concentration_for_well(well_id, concentrations):
    """Возвращает концентрацию для конкретного well_id"""
    well_letter = extract_well_letter(well_id)
    if well_letter == 'A':
        return ""
    else:
        return concentrations.get(well_letter, "")


def find_data_rows(df):
    """Находит строки с данными в таблице"""
    data_rows = []
    for idx, row in df.iterrows():
        try:
            col1_value = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else ""
            if re.match(r'^[A-Fa-f]\d+', col1_value):
                data_rows.append(idx)
        except:
            continue
    return data_rows


def extract_data_with_index(df, table_type):
    """Извлекает данные с добавлением индекса строки для корректного объединения"""
    data = []
    data_row_indices = find_data_rows(df)

    st.write(f"Найдено {len(data_row_indices)} строк с данными")

    for idx in data_row_indices:
        row = df.iloc[idx]
        try:
            experiment_id = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ""
            well_id = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else ""
            time_str = str(row.iloc[2]).strip() if len(row) > 2 and pd.notna(row.iloc[2]) else ""

            if not experiment_id or not well_id:
                continue

            # Создаем уникальный ключ для объединения
            merge_key = f"{experiment_id}_{well_id}_{idx}"

            if table_type == 1:
                record = {
                    'merge_key': merge_key,
                    'experiment_id': experiment_id,
                    'well_id': well_id,
                    'time': time_str,
                    'distance_moved': safe_float(row.iloc[3]),
                    'velocity': safe_float(row.iloc[4]),
                    'movement1': safe_float(row.iloc[5]),
                    'movement2': safe_float(row.iloc[6])
                }
            elif table_type == 2:
                record = {
                    'merge_key': merge_key,
                    'experiment_id': experiment_id,
                    'well_id': well_id,
                    'heading': safe_float(row.iloc[3]),
                    'turn_angle': safe_float(row.iloc[4]),
                    'angular_velocity': safe_float(row.iloc[5]),
                    'meander1': safe_float(row.iloc[6]),
                    'meander2': safe_float(row.iloc[7])
                }
            else:  # table_type == 3
                record = {
                    'merge_key': merge_key,
                    'experiment_id': experiment_id,
                    'well_id': well_id,
                    'cw_rotation': safe_float(row.iloc[3]),
                    'ccw_rotation': safe_float(row.iloc[4])
                }

            data.append(record)

        except Exception as e:
            continue

    return pd.DataFrame(data)


def safe_float(value):
    """Безопасное преобразование в float"""
    try:
        if pd.isna(value) or value == '' or str(value).strip() == '':
            return None
        value_str = str(value).replace(',', '.')
        return float(value_str)
    except:
        return None


def merge_tables_corrected(df1, df2, df3, exposure_time, compound, concentrations):
    """
    Корректное объединение таблиц с использованием merge_key
    """
    st.info("Извлечение данных из таблиц...")

    # Извлекаем данные с merge_key
    data1 = extract_data_with_index(df1, 1)
    data2 = extract_data_with_index(df2, 2)
    data3 = extract_data_with_index(df3, 3)

    st.write(f"Извлечено строк: Таблица 1 - {len(data1)}, Таблица 2 - {len(data2)}, Таблица 3 - {len(data3)}")

    if len(data1) == 0 or len(data2) == 0 or len(data3) == 0:
        st.error("Не удалось извлечь данные из одной из таблиц")
        return pd.DataFrame()

    # Объединяем таблицы по merge_key
    try:
        merged = data1.merge(data2, on='merge_key', how='inner', suffixes=('', '_y'))
        merged = merged.merge(data3, on='merge_key', how='inner', suffixes=('', '_z'))

        st.write(f"После объединения по merge_key: {len(merged)} строк")

        # Удаляем дублирующиеся столбцы
        columns_to_drop = [col for col in merged.columns if col.endswith('_y') or col.endswith('_z')]
        merged = merged.drop(columns=columns_to_drop)

    except Exception as e:
        st.error(f"Ошибка при объединении таблиц: {e}")
        return pd.DataFrame()

    # Создаем финальную таблицу
    result_data = []

    for _, row in merged.iterrows():
        time_minutes = parse_time_interval(row['time'])
        light_status = calculate_light_status(time_minutes)
        test_control = get_test_control(row['well_id'])
        concentration = get_concentration_for_well(row['well_id'], concentrations)

        result_row = {
            'experiment_id': row['experiment_id'],
            'exposure_time': exposure_time,
            'well_id': row['well_id'],
            'Test/Control': test_control,
            'Compound': compound if test_control == "Test" else "",
            'Concentration': concentration,
            'Time': row['time'],
            'Light': light_status,
            'Distance moved': row['distance_moved'],
            'Velocity': row['velocity'],
            'Movement': row['movement1'],
            'Movement_2': row['movement2'],
            'Heading': row['heading'],
            'Turn angle': row['turn_angle'],
            'Angular velocity': row['angular_velocity'],
            'Meander': row['meander1'],
            'Meander_2': row['meander2'],
            'CW Rotation': row['cw_rotation'],
            'CCW Rotation': row['ccw_rotation']
        }

        result_data.append(result_row)

    result_df = pd.DataFrame(result_data)

    # Проверяем качество данных
    if len(result_df) != len(data1):
        st.warning(f"Количество строк изменилось: было {len(data1)}, стало {len(result_df)}")

    return result_df


def add_column_headers(result_df):
    """
    Добавляет три статичные строки с названиями столбцов МЕЖДУ основной строкой заголовков и данными
    """
    # Создаем DataFrame с основными заголовками
    column_names = [
        'experiment_id', 'exposure_time', 'well_id', 'Test/Control', 'Compound',
        'Concentration', 'Time', 'Light', 'Distance moved', 'Velocity',
        'Movement', 'Movement_2', 'Heading', 'Turn angle', 'Angular velocity',
        'Meander', 'Meander_2', 'CW Rotation', 'CCW Rotation'
    ]

    # Создаем строку с основными заголовками
    main_header_row = pd.DataFrame([column_names], columns=column_names)

    # Создаем три строки с дополнительными заголовками
    # Первая строка дополнительных заголовков (вторая строка в таблице)
    header_row1 = {col: "" for col in column_names}
    header_row1['Distance moved'] = "Center-point"
    header_row1['Velocity'] = "Center-point"
    header_row1['Movement'] = "Moving / Center-point"
    header_row1['Movement_2'] = "Not Moving / Center-point"
    header_row1['Heading'] = "Center-point"
    header_row1['Turn angle'] = "Center-point / relative"
    header_row1['Angular velocity'] = "Center-point / relative"
    header_row1['Meander'] = "Center-point / relative"
    header_row1['Meander_2'] = "Center-point / relative"
    header_row1['CW Rotation'] = "Center-point / Clockwise"
    header_row1['CCW Rotation'] = "Center-point / Counter clockwise"

    # Вторая строка дополнительных заголовков (третья строка в таблице)
    header_row2 = {col: "" for col in column_names}
    header_row2['Distance moved'] = "Total"
    header_row2['Velocity'] = "Mean"
    header_row2['Movement'] = "Cumulative Duration"
    header_row2['Movement_2'] = "Cumulative Duration"
    header_row2['Heading'] = "Mean"
    header_row2['Turn angle'] = "Mean"
    header_row2['Angular velocity'] = "Mean"
    header_row2['Meander'] = "Mean"
    header_row2['Meander_2'] = "Total"
    header_row2['CW Rotation'] = "Frequency"
    header_row2['CCW Rotation'] = "Frequency"

    # Третья строка дополнительных заголовков (четвертая строка в таблице)
    header_row3 = {col: "" for col in column_names}
    header_row3['Distance moved'] = "mm"
    header_row3['Velocity'] = "mm/s"
    header_row3['Movement'] = "s"
    header_row3['Movement_2'] = "s"
    header_row3['Heading'] = "deg"
    header_row3['Turn angle'] = "deg"
    header_row3['Angular velocity'] = "deg/s"
    header_row3['Meander'] = "deg/mm"
    header_row3['Meander_2'] = "deg/mm"
    # CW Rotation и CCW Rotation остаются пустыми в третьей строке

    # Создаем DataFrame с тремя строками дополнительных заголовков
    additional_headers_df = pd.DataFrame([header_row1, header_row2, header_row3])

    # Собираем финальный DataFrame в правильном порядке:
    # 1. Основные заголовки
    # 2. Три строки дополнительных заголовков
    # 3. Все данные из result_df
    final_df = pd.concat([main_header_row, additional_headers_df, result_df], ignore_index=True)

    return final_df


if __name__ == "__main__":
    main()
