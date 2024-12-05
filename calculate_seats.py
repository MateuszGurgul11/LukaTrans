import streamlit as st
import pandas as pd

def read_student_data(file, file_index):
    df = pd.read_excel(file)
    df.columns = df.columns.str.strip()  # Usuwa nadmiarowe spacje z nazw kolumn
    df['Nr'] = df['Nr'].apply(lambda x: f"{file_index}_{x}")
    return df

def display_students_in_one_line(df, col1):
    for index, row in df.iterrows():
        try:
            student_info = (
                f"ID: {row['Nr']}, "
                f"Uczeń: {row['Uczeń']}, "
                f"Adres: {row['Adres']}, "
                f"Poniedziałek: {row.get('Poniedziałek - Odbiór', 'Brak danych')}, "
                f"Wtorek: {row.get('Wtorek - Odbiór', 'Brak danych')}, "
                f"Środa: {row.get('Środa - Odbiór', 'Brak danych')}, "
                f"Czwartek: {row.get('Czwartek - Odbiór', 'Brak danych')}, "
                f"Piątek: {row.get('Piątek - Odbiór', 'Brak danych')}"
            )
            col1.write(student_info)
        except KeyError as e:
            col1.error(f"Brakuje kolumny: {e}")
        col1.write("---")


def display_groups(col2):
    groups = {f"Grupa {i+1}": {"Samochód": f"Samochód {i+1}", "Uczniowie": []} for i in range(10)}
    for group_name, group_info in groups.items():
        col2.subheader(f"{group_name}")
        col2.write(f"Samochód: {group_info['Samochód']}")
        col2.write("Przypisani uczniowie:")
        if group_info["Uczniowie"]:
            for student in group_info["Uczniowie"]:
                col2.write(f"- {student}")
        else:
            col2.write("Brak przypisanych uczniów.")
        col2.write("---")
    return groups

def calculate_seats_interface():
    st.title("Grupowanie uczniów")
    uploaded_files = st.file_uploader("Prześlij pliki (.xls, .xlsx)", type=["xls", "xlsx"], accept_multiple_files=True)

    if uploaded_files:
        try:
            df_list = []
            for file_index, uploaded_file in enumerate(uploaded_files):
                df = read_student_data(uploaded_file, file_index)
                df_list.append(df)

            df_students = pd.concat(df_list, ignore_index=True)
            st.success("Dane wczytane!")

            # Podział na dwie kolumny
            col1, col2 = st.columns(2)

            # Wyświetlenie uczniów w pierwszej kolumnie
            with col1:
                st.header("Lista uczniów")
                display_students_in_one_line(df_students, col1)

            # Wyświetlenie grup w drugiej kolumnie
            with col2:
                st.header("Grupy i samochody")
                groups = display_groups(col2)

        except ValueError as e:
            st.error(e)
