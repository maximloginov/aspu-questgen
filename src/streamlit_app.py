import streamlit as st
from dataclasses import dataclass
from typing import List, Dict, Optional
import PyPDF2
import json
import random

@dataclass
class Question:
    text: str
    type: str  # 'short_text', 'multiple_choice', 'ordering'
    answers: List[str]
    correct_answers: List[int]
    distractors: List[str]
    metadata: Dict = None

class TextProcessor:
    def __init__(self):
        pass

    def extract_sentences(self, text: str) -> List[str]:
        sentences = [s.strip() for s in text.split('.') if s.strip()]
        return sentences

    def analyze_complexity(self, text: str) -> float:
        # Simple complexity metric based on sentence length
        sentences = self.extract_sentences(text)
        avg_length = sum(len(s.split()) for s in sentences) / len(sentences)
        return avg_length

class DistractorGenerator:
    @staticmethod
    def generate_short_answer_distractors(correct_answer: str, num_distractors: int = 3) -> List[str]:
        distractors = []
        words = correct_answer.lower().split()
        for _ in range(num_distractors):
            # Generate plausible distractors by modifying word order or replacing similar words
            distractor = ' '.join(words[::-1])  # Simple reversal
            distractors.append(distractor)
        return distractors[:num_distractors]

    @staticmethod
    def generate_multiple_choice_distractors(correct_answer: str, num_options: int = 4) -> List[str]:
        distractors = [
            f"{correct_answer} but faster",
            f"Not {correct_answer}",
            f"{correct_answer} and slower"
        ]
        return [correct_answer] + distractors[:num_options-1]

class QuizGenerator:
    def __init__(self):
        self.processor = TextProcessor()
        self.distractor_gen = DistractorGenerator()

    def generate_quiz(self, file_data: str, question_counts: Dict[str, int]) -> List[Question]:
        sentences = self.processor.extract_sentences(file_data)
        questions = []

        # Generate short text questions
        for i in range(question_counts['short_text']):
            sentence = random.choice(sentences)
            question = Question(
                text=f"What is the main idea of: '{sentence}'?",
                type='short_text',
                answers=[],
                correct_answers=[0],
                distractors=self.distractor_gen.generate_short_answer_distractors(sentence),
                metadata={'source': 'document'}
            )
            questions.append(question)

        # Generate multiple choice questions
        for i in range(question_counts['multiple_choice']):
            sentence = random.choice(sentences)
            question = Question(
                text=f"What best describes: '{sentence}'?",
                type='multiple_choice',
                answers=['Accurate', 'Partially Accurate', 'Incorrect'],
                correct_answers=[0],
                distractors=self.distractor_gen.generate_multiple_choice_distractors('Accurate'),
                metadata={'source': 'document'}
            )
            questions.append(question)

        return questions

class StreamlitQuizApp:
    def __init__(self):
        self.quiz_generator = QuizGenerator()
        self.setup_ui()

    def setup_ui(self):
        st.title("Quiz Generator")
        st.subheader("Upload your document to generate questions")

        # File upload section
        uploaded_file = st.file_uploader("Choose a PDF or text file",
                                       type=['pdf', 'txt'])

        if uploaded_file is not None:
            # Display question type configuration
            st.header("Configure Question Types")
            col1, col2, col3 = st.columns(3)

            with col1:
                short_text_count = st.number_input(
                    "Short Text Questions",
                    min_value=0,
                    value=3
                )

            with col2:
                mc_count = st.number_input(
                    "Multiple Choice Questions",
                    min_value=0,
                    value=3
                )

            with col3:
                ordering_count = st.number_input(
                    "Ordering Questions",
                    min_value=0,
                    value=3
                )

            if st.button("Generate Quiz"):
                # Process file and generate quiz
                file_data = self.handle_file_upload(uploaded_file)
                question_counts = {
                    'short_text': int(short_text_count),
                    'multiple_choice': int(mc_count),
                    'ordering': int(ordering_count)
                }

                questions = self.quiz_generator.generate_quiz(file_data, question_counts)
                self.preview_questions(questions)

    def handle_file_upload(self, uploaded_file):
        if uploaded_file.name.endswith('.pdf'):
            pdf_reader = PyPDF2.PdfReader(uploaded_file)
            return '\n'.join(page.extract_text() for page in pdf_reader.pages)
        return uploaded_file.read().decode('utf-8')

    def preview_questions(self, questions: List[Question]):
        st.header("Generated Questions Preview")
        selected_questions = []

        for idx, question in enumerate(questions):
            with st.expander(f"Question {idx + 1} ({question.type})"):
                st.write(question.text)

                if question.type == 'multiple_choice':
                    options = question.answers + question.distractors
                    random.shuffle(options)

                    cols = st.columns(len(options))
                    for i, option in enumerate(options):
                        with cols[i]:
                            if st.checkbox(
                                option,
                                key=f"question_{idx}_option_{i}",
                                value=True
                            ):
                                selected_questions.append(idx)

                elif question.type == 'short_text':
                    st.text_area(
                        "Answer:",
                        height=100,
                        key=f"question_{idx}_answer"
                    )
                    if st.checkbox(
                        "Include in export",
                        key=f"question_{idx}_include",
                        value=True
                    ):
                        selected_questions.append(idx)
        # Add export section
        st.header("Export Questions")
        format_types = ['JSON', 'TXT', 'GIFT']
        selected_format = st.selectbox("Select export format", format_types)

        if st.button("Export Questions"):
            selected_questions = [questions[i] for i in st.session_state.selected_questions]
            export_data = self.export_questions(selected_questions, selected_format.lower())

            st.download_button(
                label="Download File",
                data=export_data,
                file_name=f"quiz.{selected_format.lower()}",
                mime=f"application/{selected_format.lower()}"
            )

    def export_questions(self, questions: List[Question], format_type: str):
        if format_type == 'json':
            return json.dumps([q.__dict__ for q in questions])
        elif format_type == 'txt':
            return '\n\n'.join(f"{q.text}\nAnswers: {', '.join(q.answers)}"
                             for q in questions)
        elif format_type == 'gift':
            gift_format = []
            for i, q in enumerate(questions):
                if q.type == 'multiple_choice':
                    gift_format.append(f'::Q{i+1}::{q.text}{{')
                    gift_format.append(f'$A={q.correct_answers[0]+1}')
                    gift_format.extend(q.answers + q.distractors)
                    gift_format.append('}')
            return '\n'.join(gift_format)

# Run the application
if __name__ == "__main__":
    app = StreamlitQuizApp()
