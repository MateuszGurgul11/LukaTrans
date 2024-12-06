import streamlit as st
import pandas as pd
from streamlit_sortables import sort_items
import urllib.parse

def read_student_data(file, file_index):
    df = pd.read_excel(file)
    df.columns = df.columns.str.strip()
    df['Nr'] = df['Nr'].apply(lambda x: f"{file_index}_{x}")
    return df

def display_students_in_one_line(df):
    student_list = []
    for index, row in df.iterrows():
        try:
            student_info = (
                f"ID: {row['Nr']}, "
                f"Uczeń: {row['Uczeń']}, "
                f"Adres: {row['Adres']}, "
                f"Poniedziałek: {row.get('Poniedziałek-odbiór', 'Brak danych')}, "
                f"Wtorek: {row.get('Wtorek-odbiór', 'Brak danych')}, "
                f"Środa: {row.get('Środa-odbiór', 'Brak danych')}, "
                f"Czwartek: {row.get('Czwartek-odbiór', 'Brak danych')}, "
                f"Piątek: {row.get('Piątek-odbiór', 'Brak danych')}")
            student_list.append((row['Nr'], student_info))
        except KeyError as e:
            st.error(f"Brakuje kolumny: {e}")
    return student_list

def display_groups(groups):
    for group_name, group_info in groups.items():
        remove_student = st.selectbox(
                f"Usuń ucznia z {group_name}", 
                options=["---"] + group_info["Uczniowie"],
                key=f"remove_{group_name}"
            )
        if remove_student != "---" and st.button(f"Usuń {remove_student} z {group_name}", key=f"remove_button_{group_name}"):
                group_info["Uczniowie"].remove(remove_student)
                st.success(f"Usunięto ucznia: {remove_student} z {group_name}")
        st.subheader(f"{group_name}")
        st.write(f"Samochód: {group_info['Samochód']}")
        st.write(f"Miejsca: {group_info['Miejsca']}")
        st.write("---")

def generate_google_maps_link(addresses, start_point, end_point):
    base_url = "https://www.google.com/maps/dir/"
    encoded_addresses = [urllib.parse.quote(address) for address in addresses]
    return base_url + urllib.parse.quote(start_point) + "/" + "/".join(encoded_addresses) + "/" + urllib.parse.quote(end_point)

def assign_student_to_group(student, selected_group, groups):
    current_group = groups[selected_group]
    if len(current_group["Uczniowie"]) < current_group["Miejsca"]:
        current_group["Uczniowie"].append(student)
        st.success(f"Przypisano ucznia: {student} do {selected_group}")
    else:
        next_group = find_next_group(selected_group, groups)
        if next_group:
            groups[next_group]["Uczniowie"].append(student)
            st.warning(f"Grupa {selected_group} jest pełna. Uczeń {student} został przypisany do {next_group}.")

def find_next_group(current_group_name, groups):
    group_names = list(groups.keys())
    current_index = group_names.index(current_group_name)
    for i in range(current_index + 1, len(group_names)):
        if len(groups[group_names[i]]["Uczniowie"]) < groups[group_names[i]]["Miejsca"]:
            return group_names[i]
    st.error("Brak dostępnych grup z wolnymi miejscami.")
    return None

def save_groups_to_excel(groups):
    writer = pd.ExcelWriter("grupy_uczniow.xlsx", engine='xlsxwriter')

    workbook = writer.book
    worksheet = workbook.add_worksheet("Grupy")
    writer.sheets["Grupy"] = worksheet

    col_index = 0
    for group_name, group_info in groups.items():
        addresses = [
            student.split(", ")[2].split(": ")[1] for student in group_info["Uczniowie"]
        ]
        if addresses:
            start_point = "Olimpijska 1, 61-872 Poznań"
            end_point = "Bydgoska 4a, 61-127 Poznań" if "0_" in group_info["Uczniowie"][0] else "Nieszawska 21, 61-021 Poznań"
            maps_link = generate_google_maps_link(addresses, start_point, end_point)
        else:
            maps_link = "Brak danych"

        worksheet.write(0, col_index, group_name)
        worksheet.write(1, col_index, maps_link)

        for row_index, student in enumerate(group_info["Uczniowie"], start=2):
            student_name = student.split(", ")[1].split(": ")[1]  # Extract only the student's name
            worksheet.write(row_index, col_index, student_name)

        col_index += 1

    writer.close()
    st.success("Grupy zostały zapisane do pliku Excel.")
    st.download_button(
        label="Pobierz plik Excel",
        data=open("grupy_uczniow.xlsx", "rb").read(),
        file_name="grupy_uczniow.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

def calculate_seats_interface():
    st.title("Grupowanie uczniów")

    if "groups" not in st.session_state:
        st.session_state.groups = {
            "Grupa 1": {"Samochód": "Mercedes Sprinter", "Miejsca": 19, "Uczniowie": []},
            "Grupa 2": {"Samochód": "Ford Transit", "Miejsca": 16, "Uczniowie": []},
            "Grupa 3": {"Samochód": "Fiat Ducato", "Miejsca": 15, "Uczniowie": []},
            "Grupa 4": {"Samochód": "Fiat Ducato 2", "Miejsca": 15, "Uczniowie": []},
            "Grupa 5": {"Samochód": "VW Transporter", "Miejsca": 7, "Uczniowie": []},
            "Grupa 6": {"Samochód": "VW Transporter 2", "Miejsca": 7, "Uczniowie": []},
            "Grupa 7": {"Samochód": "VW Transporter 3", "Miejsca": 7, "Uczniowie": []},
            "Grupa 8": {"Samochód": "VW Transporter 4", "Miejsca": 7, "Uczniowie": []},
            "Grupa 9": {"Samochód": "Ford Custom", "Miejsca": 7, "Uczniowie": []},
            "Grupa 10": {"Samochód": "Mercedes Elektryk", "Miejsca": 7, "Uczniowie": []},
        }

    if "remaining_students" not in st.session_state:
        st.session_state.remaining_students = []

    uploaded_files = st.file_uploader("Prześlij pliki (.xls, .xlsx)", type=["xls", "xlsx"], accept_multiple_files=True)

    if uploaded_files:
        try:
            df_list = []
            for file_index, uploaded_file in enumerate(uploaded_files):
                df = read_student_data(uploaded_file, file_index)
                df_list.append(df)

            df_students = pd.concat(df_list, ignore_index=True)
            st.success("Dane wczytane!")

            if not st.session_state.remaining_students:
                st.session_state.remaining_students = display_students_in_one_line(df_students)

            st.header("Grupy i samochody")
            selected_group = st.selectbox("Wybierz grupę", options=list(st.session_state.groups.keys()))

            if st.session_state.remaining_students:
                selected_student = st.selectbox(
                    "Wybierz ucznia do przypisania", 
                    options=[info for _, info in st.session_state.remaining_students]
                )

                if st.button("Przypisz ucznia"):
                    student_id = next(student[0] for student in st.session_state.remaining_students if student[1] == selected_student)
                    assign_student_to_group(selected_student, selected_group, st.session_state.groups)
                    st.session_state.remaining_students = [
                        student for student in st.session_state.remaining_students if student[1] != selected_student
                    ]

            st.header("Ustalanie kolejności uczniów")
            for group_name, group_info in st.session_state.groups.items():
                if group_info["Uczniowie"]:
                    st.subheader(f"{group_name}")
                    ordered_students = sort_items(
                        group_info["Uczniowie"],
                        f"sortable_{group_name}",
                        direction="vertical",
                    )
                    st.session_state.groups[group_name]["Uczniowie"] = ordered_students

                    addresses = [
                        student.split(", ")[2].split(": ")[1] for student in ordered_students
                    ]
                    if addresses:
                        start_point = "Olimpijska 1, 61-872 Poznań"
                        end_point = "Bydgoska 4a, 61-127 Poznań" if "0_" in ordered_students[0] else "Nieszawska 21, 61-021 Poznań"
                        maps_link = generate_google_maps_link(addresses, start_point, end_point)
                        st.write(f"[Trasa na Google Maps]({maps_link})")

            display_groups(st.session_state.groups)

            if st.button("Zapisz grupy"):
                save_groups_to_excel(st.session_state.groups)

        except ValueError as e:
            st.error(e)
