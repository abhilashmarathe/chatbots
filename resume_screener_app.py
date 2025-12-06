# resume_screener_app.py
import os, io, re
import numpy as np
import pandas as pd
import streamlit as st
import pdfplumber, docx
from sklearn.metrics.pairwise import cosine_similarity
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

st.set_page_config(page_title="Resume Screener Bot", layout="wide")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

EMBED_MODEL = "text-embedding-3-small"

# -------- Resume Parsing --------
def extract_pdf(data):
    txt = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for pg in pdf.pages:
            txt.append(pg.extract_text() or "")
    return "\n".join(txt)

def extract_docx(data):
    doc = docx.Document(io.BytesIO(data))
    return "\n".join([p.text for p in doc.paragraphs if p.text])

def parse(file):
    data = file.read()
    name = file.name.lower()
    if name.endswith(".pdf"): return extract_pdf(data)
    if name.endswith(".doc") or name.endswith(".docx"): return extract_docx(data)
    return data.decode("utf-8", errors="ignore")

# -------- Embedding --------
def embed(text):
    text = text[:30000]
    r = client.embeddings.create(
        model=EMBED_MODEL,
        input=text
    )
    return np.array(r.data[0].embedding)

def cos(a, b):
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))

def extract_exp(txt):
    m = re.findall(r'(\d{1,2})\s+years', txt.lower())
    return int(m[0]) if m else 0

# -------- App UI --------
st.title("🔎 Resume Screener Bot — Streamlit")

resumes = st.file_uploader("Upload Resumes", type=["pdf","doc","docx","txt"], accept_multiple_files=True)
jd = st.text_area("Paste Job Description", height=260)

topk = st.slider("Top K candidates", 1, 10, 5)
run = st.button("Run Screening")

if run:
    if not OPENAI_API_KEY:
        st.error("Set OPENAI_API_KEY first.")
    elif not resumes:
        st.error("Upload resumes")
    elif not jd.strip():
        st.error("Paste job description")
    else:
        st.info("Processing resumes... calling OpenAI embeddings")
        jd_emb = embed(jd)

        jd_words = set(re.findall(r"\b[a-zA-Z]{4,}\b", jd.lower()))
        results = []

        for r in resumes:
            text = parse(r)
            emb = embed(text)
            sim = cos(emb, jd_emb)

            res_words = set(re.findall(r"\b[a-zA-Z]{4,}\b", text.lower()))
            overlap = len(jd_words.intersection(res_words))

            exp = extract_exp(text)
            score = 0.6*sim + 0.25*(overlap/(len(jd_words)+1)) + 0.15*min(exp/10,1)

            results.append({
                "name": r.name,
                "text": text,
                "similarity": sim,
                "overlap": overlap,
                "experience": exp,
                "score": round(score, 3)
            })

        ranked = sorted(results, key=lambda x: x["score"], reverse=True)[:topk]
        df = pd.DataFrame(ranked)[["name","score","similarity","overlap","experience"]]
        st.subheader("🏅 Ranked Candidates")
        st.dataframe(df)

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("⬇ Download CSV", csv, "shortlisted.csv")

        for r in ranked:
            with st.expander(f"{r['name']} — score {r['score']}"):
                st.write(f"Similarity: {r['similarity']:.3f} | Overlap: {r['overlap']} | Experience: {r['experience']} yrs")
                st.write("📌 Resume Highlights")

                highlight_words = sorted(list(jd_words))[:20]
                for line in r["text"].split("\n"):
                    if any(kw in line.lower() for kw in highlight_words):
                        st.markdown(f"> {line}")
