import streamlit as st
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import os
import asyncio
import json
import pandas as pd
import re
import unicodedata
import math

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

# Zmiana modelu na poprawny
llm = ChatOpenAI(temperature=0.1, model_name="gpt-4o-mini", openai_api_key=api_key)

calculate_seats_prompt_template = """
SYSTEM PROMPT:
You are an AI assistant specializing in geolocation and route optimization.

Given the following student data and vehicle capacities, divide the students into 10 groups, each assigned to a specific vehicle. The goal is to assign students to groups so that the total number of students in each group does not exceed the vehicle's capacity, and to ensure that students in each group are geographically close to one another to optimize the route.

Rules:

1. There are exactly 10 groups, each assigned to a specific vehicle with a given capacity:

- **Group 1**: Mercedes Sprinter – capacity 19 students
- **Group 2**: Ford Transit – capacity 16 students
- **Group 3**: Fiat Ducato – capacity 15 students
- **Group 4**: Fiat Ducato 2 – capacity 15 students
- **Group 5**: VW Transporter – capacity 7 students
- **Group 6**: VW Transporter 2 – capacity 7 students
- **Group 7**: VW Transporter 3 – capacity 7 students
- **Group 8**: VW Transporter 4 – capacity 7 students
- **Group 9**: Ford Custom – capacity 7 students
- **Group 10**: Mercedes Elektryk – capacity 7 students

2. Assign students to the groups so that:

- The number of students in each group does not exceed the vehicle's capacity.
- Students in each group are geographically close to each other to optimize the route.

3. Calculate approximate distances between student addresses to group them in a way that minimizes the total travel distance for each group.

4. If necessary, distribute any remaining students while respecting vehicle capacities and optimizing for proximity.

Input Data:
{students_data}

Your response must be a valid JSON object:

{{
    "groups": [
        {{
            "group_id": 1,
            "vehicle": "Mercedes Sprinter",
            "capacity": 19,
            "students": [
                {{
                    "id": "Student ID",
                    "name": "Student Name",
                    "address": "Student Address",
                    "pickup_time": "Pickup Time"
                }}
            ]
        }},
    ]
}}

IMPORTANT: Provide only the JSON object as your response.
"""

def remove_polish_characters(text):
    if isinstance(text, str):
        # Usuwanie polskich znaków diakrytycznych
        return unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode('utf-8')
    return text

def read_student_data(file, file_index):
    df = pd.read_excel(file)
    for col in df.select_dtypes(include=['object']).columns:
        df[col] = df[col].apply(remove_polish_characters)
    # Add prefix to IDs to ensure uniqueness across files
    df['Nr'] = df['Nr'].apply(lambda x: f"{file_index}_{x}")
    return df

def convert_df_to_text(df):
    rows = []
    for index, row in df.iterrows():
        student_text = f"ID: {row['Nr']}, Name: {row['Uczeń']}, Address: {row['Adres']}, "
        student_text += f"Pickup times: Poniedziałek: {row['Poniedziałek-odbiór']}, Wtorek: {row['Wtorek-odbiór']}, "
        student_text += f"Środa: {row['Środa-odbiór']}, Czwartek: {row['Czwartek-odbiór']}, Piątek: {row['Piątek-odbiór']}."
        rows.append(student_text)
    return "\n".join(rows)

async def async_calculate_seats(chain, students_data):
    return await chain.ainvoke(students_data)

def run_async_task(chain, students_data):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop.run_until_complete(async_calculate_seats(chain, students_data))

def display_results(groups_json):
    """
    Displays the grouped student results and handles checkboxes with state memory in the session.
    """
    st.header("Wyniki grupowania uczniów:")
    for group in groups_json.get("groups", []):
        if not group.get('students'):  # Check if the students list is empty
            continue  # Skip the group if it has no students

        group_key = f"group_{group['group_id']}"
        vehicle = group.get('vehicle', 'Brak pojazdu')
        capacity = group.get('capacity', 'N/A')
        st.subheader(f"Grupa {group['group_id']} - {vehicle} (Pojemność: {capacity})")
        
        # Store group state in session
        if group_key not in st.session_state:
            st.session_state[group_key] = {
                student['id']: False for student in group['students']
            }
        
        for i, student in enumerate(group["students"]):
            student_key = f"{group_key}_student_{student['id']}_{i}"
            if student_key not in st.session_state:
                st.session_state[student_key] = True
            
            checked = st.checkbox(
                f"{student['name']} - {student['address']} ({student['pickup_time']})",
                key=student_key,
                value=st.session_state[student_key],
            )
            st.session_state[group_key][student['id']] = checked
        
        st.write("---")

def calculate_seats_interface():
    """
    Main function handling the Streamlit interface.
    """
    st.title("Grupowanie uczniów")
    uploaded_files = st.file_uploader("Prześlij pliki (.xls, .xlsx)", type=["xls", "xlsx"], accept_multiple_files=True)
    if uploaded_files:
        try:
            # Reading data from multiple files
            df_list = []
            for file_index, uploaded_file in enumerate(uploaded_files):
                df = read_student_data(uploaded_file, file_index)
                df_list.append(df)
            
            # Concatenating all DataFrames into one
            df_students = pd.concat(df_list, ignore_index=True)
            st.success("Dane wczytane!")
            st.table(df_students)

            if st.button("Pogrupuj uczniów"):
                with st.spinner("Przetwarzanie..."):
                    try:
                        # Splitting data into smaller batches
                        max_students_per_batch = 25
                        total_students = len(df_students)
                        num_batches = math.ceil(total_students / max_students_per_batch)
                        all_groups = []
                        group_id_counter = 1

                        for batch_num in range(num_batches):
                            start_idx = batch_num * max_students_per_batch
                            end_idx = min((batch_num + 1) * max_students_per_batch, total_students)
                            batch_df = df_students.iloc[start_idx:end_idx]
                            students_text_batch = convert_df_to_text(batch_df)

                            calculate_seats_prompt = PromptTemplate.from_template(calculate_seats_prompt_template)
                            calculate_seats_chain = calculate_seats_prompt | llm
                            response_text = run_async_task(calculate_seats_chain, {"students_data": students_text_batch})
                            response_content = response_text.content

                            # Debugging the response
                            st.write("Odpowiedź modelu przed parsowaniem:", response_content)

                            try:
                                # Remove code block markers and whitespace
                                response_content = response_content.strip().strip('```json').strip('```').strip()
                                groups_json = json.loads(response_content)
                            except json.JSONDecodeError as e:
                                st.error(f"Błąd podczas parsowania JSON: {e}")
                                return

                            # Update group_id to be unique
                            for group in groups_json.get("groups", []):
                                group['group_id'] = group_id_counter
                                group_id_counter += 1
                            all_groups.extend(groups_json.get("groups", []))

                        # Save groups in session
                        st.session_state["grouped_students"] = {"groups": all_groups}

                    except Exception as e:
                        st.error(f"Błąd: {e}")

        except ValueError as e:
            st.error(e)

    # Display saved groups in session
    if "grouped_students" in st.session_state:
        st.subheader("Grupy w sesji:")
        display_results(st.session_state["grouped_students"])