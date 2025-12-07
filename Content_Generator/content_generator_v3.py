# content_generator_ultra.py
import os
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI
from reportlab.pdfgen import canvas
from io import BytesIO
from datetime import datetime

# --------------------------
# Setup
# --------------------------
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = None
if OPENAI_API_KEY:
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
    except Exception as e:
        st.warning(f"OpenAI client init error: {e}")

st.set_page_config(page_title="Content Generator Ultra", layout="wide")
st.title("✍️ Content Generator — Ultra (v3)")

# --------------------------
# Templates & Languages
# --------------------------
MODEL = "gpt-4o-mini"

TEMPLATES = {
    "Email": "Write a {tone} email (~{length} words) promoting {product} for {audience}. Add subject + a short CTA.",
    "Social Post": "Write a {tone} social media caption (~{length} words) for {product}. Include 1 hashtag.",
    "Blog Outline": "Write a full blog outline for {product} targeting {audience}. Provide H1, H2s and 3 bullets per H2.",
    "YouTube Script": "Write a {tone} YouTube video script about {product} for {audience}. Include intro, hook, 3 main points, and CTA.",
    "Ad Copy": "Write a high-converting {tone} ad copy (~{length} words) for {product} aimed at {audience}.",
    "Product Description": "Write an engaging {tone} product description (~{length} words) for {product}.",
    "Cold Outreach DM": "Write a {tone} cold outreach message (~{length} words) to pitch {product} to {audience}."
}

LANGUAGES = ["English", "Hindi", "Marathi", "Spanish", "French"]

# --------------------------
# Session state
# --------------------------
if "history" not in st.session_state:
    # history is a list of dicts: {id, timestamp, kind, params, text}
    st.session_state.history = []

# --------------------------
# Helpers
# --------------------------
def make_prompt(kind, product, audience, tone, length, language):
    base = TEMPLATES.get(kind, TEMPLATES["Email"]).format(
        tone=tone, length=length, product=product, audience=audience
    )
    prompt = f"Please respond in {language}. {base}"
    return prompt

def generate_text(kind, product, audience, tone, length, language, temperature, max_tokens=800):
    if client is None:
        raise RuntimeError("OpenAI client is not initialized. Set OPENAI_API_KEY in .env or env vars.")
    prompt = make_prompt(kind, product, audience, tone, length, language)
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You are a helpful, professional marketing copywriter."},
            {"role": "user", "content": prompt}
        ],
        temperature=float(temperature),
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content

def generate_pdf_bytes(text: str) -> BytesIO:
    buffer = BytesIO()
    p = canvas.Canvas(buffer)
    width, height = 560, 800
    x_margin, y = 40, height - 40
    for paragraph in text.split("\n"):
        lines = []
        # break long lines
        while len(paragraph) > 110:
            cutoff = paragraph.rfind(" ", 0, 110)
            if cutoff == -1:
                cutoff = 110
            lines.append(paragraph[:cutoff])
            paragraph = paragraph[cutoff:].lstrip()
        lines.append(paragraph)
        for line in lines:
            p.drawString(x_margin, y, line)
            y -= 16
            if y < 40:
                p.showPage()
                y = height - 40
    p.save()
    buffer.seek(0)
    return buffer

def add_to_history(kind, params, text):
    entry = {
        "id": len(st.session_state.history) + 1,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "kind": kind,
        "params": params,
        "text": text
    }
    st.session_state.history.append(entry)
    return entry

def render_copy_widget(text, uid):
    # Small HTML widget to copy to clipboard
    safe_text = text.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")
    html = f"""
    <div>
      <button onclick="navigator.clipboard.writeText('{safe_text}')">📋 Copy</button>
    </div>
    """
    st.components.v1.html(html, height=40)

# --------------------------
# UI - Inputs
# --------------------------
with st.sidebar:
    st.header("🎛 Generation Settings")
    kind = st.selectbox("Content type", list(TEMPLATES.keys()))
    product = st.text_input("Product / Service", "Acme CRM")
    audience = st.text_input("Target Audience", "Small business sales teams")
    tone = st.selectbox("Tone", ["Professional", "Friendly", "Funny", "Urgent", "Inspirational"])
    language = st.selectbox("Language", LANGUAGES, index=0)
    length = st.slider("Approx length (words)", 40, 800, 150)
    temperature = st.slider("Creativity (temperature)", 0.0, 1.0, 0.7, 0.05)
    n_variations = st.slider("Generate N variations on first generate", 1, 3, 1)
    st.markdown("---")
    
    if st.button("Clear History"):
        st.session_state.history = []
        st.rerun()

col1, col2 = st.columns([3,1])
with col1:
    st.header("Generate Content")
    gen_btn = st.button("🟢 Generate Content")
with col2:
    # small info panel and counts
    st.write("History items:")
    st.write(len(st.session_state.history))

# --------------------------
# Generate logic
# --------------------------
# We'll capture the baseline params for refresh/regenerate
if "last_params" not in st.session_state:
    st.session_state.last_params = None

# Handle initial generate
if gen_btn:
    if not OPENAI_API_KEY or client is None:
        st.error("OpenAI API key not configured. Please set OPENAI_API_KEY.")
    else:
        with st.spinner("Generating..."):
            params = {"product": product, "audience": audience, "tone": tone, "language": language,
                      "length": length, "temperature": temperature, "kind": kind}
            st.session_state.last_params = params
            # generate N variations and save all
            for i in range(n_variations):
                try:
                    text = generate_text(kind, product, audience, tone, length, language, temperature)
                except Exception as e:
                    st.error(f"Generation error: {e}")
                    text = f"[Error generating content: {e}]"
                entry = add_to_history(kind, params, text)
            st.rerun()


# --------------------------
# Main panel - render latest outputs and controls
# --------------------------
st.markdown("---")
st.subheader("Generated Outputs (latest first)")

if not st.session_state.history:
    st.info("No content generated yet. Use the sidebar to set parameters and click **Generate Content**.")
else:
    # Show most recent entries first
    for entry in reversed(st.session_state.history[-50:]):
        eid = entry["id"]
        meta = entry["params"]
        ts = entry["timestamp"]
        header = f"{entry['kind']} — Version {eid} • {ts}"
        st.markdown(f"### {header}")
        st.write(f"**Params:** Product: `{meta['product']}` • Audience: `{meta['audience']}` • Tone: `{meta['tone']}` • Language: `{meta['language']}` • Length: `{meta['length']}` • Temp: `{meta['temperature']}`")
        # content box
        st.text_area(f"Content-{eid}", entry["text"], height=220, key=f"ta_{eid}")
        # Row of actions: Refresh (regenerate new variant with same params), Copy, Download TXT, Download PDF
        action_col1, action_col2, action_col3, action_col4 = st.columns([1,1,1,1])
        with action_col1:
            if st.button("🔄 Refresh (new variant)", key=f"refresh_{eid}"):
                # Use last_params if available, else use this entry's params
                params_to_use = st.session_state.last_params or entry["params"]
                try:
                    new_text = generate_text(params_to_use["kind"] if "kind" in params_to_use else entry["kind"],
                                             params_to_use.get("product", meta['product']),
                                             params_to_use.get("audience", meta['audience']),
                                             params_to_use.get("tone", meta['tone']),
                                             params_to_use.get("length", meta['length']),
                                             params_to_use.get("language", meta['language']),
                                             params_to_use.get("temperature", meta['temperature']))
                except Exception as e:
                    st.error(f"Regenerate error: {e}")
                    new_text = f"[Error regenerating content: {e}]"
                add_to_history(entry["kind"], params_to_use, new_text)
                st.experimental_rerun()
        with action_col2:
            # Copy widget (small HTML+JS)
            # Using a safe small widget per-entry
            copy_html = f"""
            <button onclick="navigator.clipboard.writeText({repr(entry['text'])});">📋 Copy</button>
            """
            st.components.v1.html(copy_html, height=40)
        with action_col3:
            # Download TXT
            st.download_button(label="⬇ Download TXT", data=entry["text"], file_name=f"{entry['kind'].replace(' ','_')}_v{eid}.txt")
        with action_col4:
            # Download PDF
            pdf_buf = generate_pdf_bytes(entry["text"])
            st.download_button(label="⬇ Download PDF", data=pdf_buf, file_name=f"{entry['kind'].replace(' ','_')}_v{eid}.pdf", mime="application/pdf")

st.markdown("---")
st.caption("Note: History is stored in this Streamlit session. It will reset if you restart the app or clear history.")

