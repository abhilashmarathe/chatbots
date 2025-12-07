import os
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI
from reportlab.pdfgen import canvas
from io import BytesIO

st.set_page_config(page_title="Content Generator Bot", layout="wide")

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

MODEL = "gpt-4o-mini"

# More content types
TEMPLATES = {
    "Email": "Write a {tone} email (~{length} words) promoting {product} for {audience}. Add subject + CTA.",
    "Social Post": "Write a {tone} social media caption (~{length} words) for {product}. Include 1 hashtag.",
    "Blog Outline": "Write a full blog outline for {product} targeting {audience}. H1 + H2 + bullets.",
    "YouTube Script": "Write a {tone} YouTube video script about {product} for {audience}. Include intro, hook & CTA.",
    "Ad Copy": "Write a high-converting {tone} ad copy (~{length} words) for {product} for {audience}.",
    "Product Description": "Write an engaging {tone} product description (~{length} words) for {product}.",
    "Cold Outreach DM": "Write a {tone} cold outreach message to pitch {product} to {audience} (~{length} words)."
}

languages = {
    "English": "English",
    "Hindi": "Hindi",
    "Marathi": "Marathi",
    "Spanish": "Spanish",
    "French": "French"
}

# Maintain history
if "history" not in st.session_state:
    st.session_state.history = []

def generate(t, product, audience, tone, length, language, temperature):
    base_prompt = TEMPLATES[t].format(product=product, audience=audience, tone=tone, length=length)
    prompt = f"Write the response in {language}. {base_prompt}"

    r = client.chat.completions.create(
        model=MODEL,
        temperature=temperature,
        messages=[
            {"role": "system", "content": "You are a marketing and copywriting expert."},
            {"role": "user", "content": prompt}
        ]
    )
    return r.choices[0].message.content

def generate_pdf(text):
    buffer = BytesIO()
    p = canvas.Canvas(buffer)
    x, y = 50, 800
    for line in text.split("\n"):
        p.drawString(x, y, line[:95])
        y -= 18
        if y < 40:
            p.showPage()
            y = 800
    p.save()
    buffer.seek(0)
    return buffer

# Title
st.title("✍️ Content Generator Bot — Advanced Version")

# Inputs
kind = st.selectbox("Content type", list(TEMPLATES.keys()))
product = st.text_input("Product / Service", "Acme CRM")
audience = st.text_input("Target Audience", "Sales Teams")
tone = st.selectbox("Tone", ["Professional", "Friendly", "Funny", "Urgent", "Inspirational"])
language = st.selectbox("Language", list(languages.keys()))
length = st.slider("Length (words)", 60, 600, 150)
temperature = st.slider("Creativity (0 = factual, 1 = creative)", 0.0, 1.0, 0.7)

if st.button("Generate Content"):
    if not OPENAI_API_KEY:
        st.error("Set OPENAI_API_KEY first.")
    else:
        with st.spinner("Generating..."):
            output = generate(kind, product, audience, tone, length, language, temperature)
            st.subheader("📄 Generated Content")
            st.write(output)

            # Save history
            st.session_state.history.append(output)

            # Copy button
            st.code(output)
            st.button("📋 Copy to Clipboard", on_click=lambda: st.session_state.update({"clipboard": output}))

            # TXT download
            st.download_button(
                "⬇ Download as TXT",
                output,
                file_name=f"{kind.replace(' ','_')}.txt"
            )

            # PDF download
            pdf_buffer = generate_pdf(output)
            st.download_button(
                "⬇ Download as PDF",
                pdf_buffer,
                file_name=f"{kind.replace(' ','_')}.pdf"
            )

# History sidebar
with st.sidebar:
    st.header("🕒 History")
    if st.session_state.history:
        for i, h in enumerate(reversed(st.session_state.history[-10:])):
            st.text_area(f"Output-{len(st.session_state.history)-i}", h, height=120)
    else:
        st.write("No content generated yet.")
