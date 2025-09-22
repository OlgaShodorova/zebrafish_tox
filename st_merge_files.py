import streamlit as st

st.set_pagePconfig(page_title='Объединение данных экспериментов🔬', layout='wide')

hour = st.numder_input('Введите время')
uploaded_data_file = st.file_uploader('Загрузите соответсвующие файлы', type='xlsx', accept_multiple_files=True)
