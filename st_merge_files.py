import streamlit as st

st.set_page_config(page_title='Объединение данных экспериментов🔬', layout='wide')

hour = st.numder_input('Введите время', min_value=0, value=4)
uploaded_data_file = st.file_uploader('Загрузите соответсвующие файлы', type='xlsx', accept_multiple_files=True)
