# TỔNG HỢP ĐỀ XUẤT ĐỒ ÁN: PHÂN TÍCH DỮ LIỆU & TÍCH HỢP AI (TAB 6)

## PHẦN 1: ĐỀ XUẤT PHÂN TÍCH KHÍ HẬU (MỤC TIÊU 4 - PHỤC VỤ VẤN ĐÁP)

Để giải quyết Mục tiêu 4 (Phân tích Áp suất, Gió và Bức xạ mặt trời), hệ thống chuẩn bị bộ 4 câu hỏi phân tích cốt lõi bao phủ trọn vẹn các yêu cầu về biểu đồ và khai thác sâu dữ liệu của 6 Vùng khí hậu tại Việt Nam (1991 - 2025). Bộ câu hỏi này đồng thời đóng vai trò **Preset Prompts** trên giao diện AI giúp thao tác nhanh khi Vấn đáp.

### 1. Phân hóa Không gian (Tìm kiếm Hotspot Năng lượng Xanh)
* **Câu hỏi:** Địa điểm nào có tiềm năng kết hợp năng lượng Xanh (Nắng + Gió) tốt nhất?
* **Biểu đồ:** `Scatter Plot` (Trục X: Bức xạ, Trục Y: Gió, Phân màu: 6 Vùng, Size: Áp suất).
* **Mục tiêu:** Nhận diện các điểm "vàng" (ven biển Nam Trung Bộ) có bức xạ cao và gió mạnh. Khẳng định áp suất thấp không đồng nghĩa với tiềm năng năng lượng xanh cao.

### 2. Xu hướng Biến đổi Khí hậu 35 năm (Temporal Trend)
* **Câu hỏi:** Tốc độ gió, áp suất và Bức xạ mặt trời có xu hướng suy giảm hay gia tăng từ 1991 đến 2025?
* **Biểu đồ:** `Line Chart` kèm Trendline (Đường xu hướng).
* **Mục tiêu:** Phát hiện hiện tượng gió suy giảm (Wind Stilling) hoặc biến động bức xạ (Solar Dimming/Brightening) do tác động của biến đổi khí hậu toàn cầu.

### 3. Tính Bổ trợ Theo Mùa (Seasonality)
* **Câu hỏi:** Gió và Nắng có "gánh" cho nhau qua 12 tháng trong năm không?
* **Biểu đồ:** `Grouped Bar Chart` hoặc `Facet Line Chart`.
* **Mục tiêu:** Chứng minh khi mùa mưa/mây làm giảm điện mặt trời thì hệ thống gió mùa có bù đắp được năng lượng hay không. Áp dụng công thức chuẩn hóa Min-Max:
  $$S_i = \left( \frac{X_i - X_{\min}}{X_{\max} - X_{\min}} \right) \times 100\%$$

### 4. Ma trận Tương quan Nguyên nhân - Kết quả
* **Câu hỏi:** Mối tương quan giữa Áp suất, Gió, Bức xạ và các sự kiện cực đoan diễn ra như thế nào?
* **Biểu đồ:** `Heatmap / Correlation Matrix`.
* **Mục tiêu:** Giải thích tính chất vật lý (Áp suất thấp + Bức xạ cao kết hợp gió lặng sinh ra sóng nhiệt).

---

## PHẦN 2: KIẾN TRÚC TÍCH HỢP AI (HUMAN-IN-THE-LOOP & NGUYÊN TẮC KHÔNG THỰC THI NGẦM)

Hệ thống tuân thủ nghiêm ngặt nguyên tắc **"Không thực thi ngầm"**, **"Hiển thị & Giải thích code"**, và **"Con người phê duyệt"**.

### 1. Kiến trúc Hệ thống Tổng thể
* **Frontend (UI):** `Streamlit` đóng vai trò giao diện tương tác: hiển thị Preset Prompts, chat input, preview/edit mã Python, nút chấp thuận thực thi, render biểu đồ Plotly tương tác và xem Lịch sử Logs.
* **Backend (API):** Xây dựng bằng **FastAPI (Python)**. 
  * *Lý do chọn FastAPI:* Đảm bảo đồng bộ môi trường Python với Streamlit & Pandas, xử lý Async hiệu quả, dễ dàng quản lý thực thi code local và tự động tạo Swagger API Documentation (`/docs`).

### 2. Các Endpoint RESTful API (Đầy đủ theo yêu cầu đề bài)
Hệ thống triển khai 3 nhóm API chính:
1. **API AI (`POST /api/ai/generate`):**
   * Tiếp nhận prompt từ Frontend + Metadata của dataset (Tên cột, kiểu dữ liệu, 5 dòng đầu mẫu). *Không gửi file dữ liệu thô để tối ưu token & bảo mật*.
   * Gửi request tới Gemini LLM kèm System Prompt quy định: *"Không bịa số liệu, chỉ viết code Python sử dụng pandas & plotly, kèm giải thích tiếng Việt chi tiết trong comment"*.
   * Trả về JSON: `{"code": "...", "explanation": "..."}`.
2. **API Thực thi (`POST /api/execute`):**
   * Tiếp nhận đoạn code đã được người dùng **chỉnh sửa & phê duyệt** từ Frontend.
   * Thực thi mã Python trên local bằng `exec()` có kiểm soát an toàn (giới hạn `globals` chỉ bao gồm `pd`, `np`, `px`, `go`).
   * Trả về dữ liệu kết quả: Plotly JSON Figure (để render biểu đồ tương tác) và/hoặc Dataframe/Text Output.
3. **API Logs (`POST /api/logs` & `GET /api/logs`) - (Bắt buộc):**
   * `POST /api/logs`: Lưu vết toàn bộ lịch sử (Thời gian, Prompt người dùng, Code AI sinh ra, Code người dùng đã sửa/phê duyệt, Trạng thái thực thi).
   * `GET /api/logs`: Truy xuất lịch sử phục vụ việc kiểm tra/đánh giá và hiển thị trên tab Nhật ký Logs.

### 3. Luồng Giao Diện (UI Flow) trên Streamlit (3 Bước chuẩn)
1. **Bước 1: Nhận yêu cầu:** Người dùng chọn Preset Prompt hoặc nhập qua `st.chat_input()`. Frontend gọi `POST /api/ai/generate`.
2. **Bước 2: Chờ duyệt & Chỉnh sửa:** 
   * Hiển thị giải thích ngôn ngữ tự nhiên bằng `st.info()`.
   * Cho phép xem và gõ chỉnh sửa trực tiếp mã Python bằng `st.text_area()` (hoặc `streamlit-code-editor`).
3. **Bước 3: Chấp nhận & Thực thi:** 
   * Người dùng nhấn nút `st.button("Chấp nhận & Thực thi Code", type="primary")`.
   * Code đã duyệt được gửi tới `POST /api/execute`, đồng thời ghi vết qua `POST /api/logs`.
   * Hiển thị kết quả bằng biểu đồ Plotly tương tác `st.plotly_chart()` hoặc bảng dữ liệu `st.dataframe()`.

---

## PHẦN 3: LOGIC MÃ NGUỒN MINH HỌA

### 1. Code Backend API (FastAPI - `main.py`)
```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import json, datetime

app = FastAPI(title="NASA Climate AI Backend API")

# Bộ lưu trữ logs đơn giản (có thể ghi ra file logs.json hoặc SQLite)
execution_logs = []

class AIGenerateRequest(BaseModel):
    prompt: str

class ExecuteRequest(BaseModel):
    prompt: str
    original_code: str
    approved_code: str

@app.post("/api/ai/generate")
def generate_ai_code(req: AIGenerateRequest):
    # 1. Chuẩn bị Metadata
    # 2. Gọi Gemini LLM API với System Prompt
    explanation = "Đoạn code sử dụng Plotly Express để vẽ Scatter plot tương tác thể hiện mối quan hệ giữa Bức xạ và Gió."
    code = """import plotly.express as px
# Drawing Scatter Plot for Wind vs Radiation
fig = px.scatter(df, x='ALLSKY_SFC_SW_DWN', y='WS10M', color='REGION', size='PS',
                 title='Tiềm năng Năng lượng Xanh (Nắng vs Gió)')
"""
    return {"explanation": explanation, "code": code}

@app.post("/api/execute")
def execute_code(req: ExecuteRequest):
    try:
        # Đọc dữ liệu local
        df = pd.read_csv("data/nasa_climate_vietnam.csv")
        
        # Môi trường thực thi an toàn
        safe_globals = {"df": df, "pd": pd, "np": np, "px": px, "go": go}
        safe_locals = {}
        
        exec(req.approved_code, safe_globals, safe_locals)
        
        fig = safe_locals.get("fig") or safe_globals.get("fig")
        fig_json = json.loads(fig.to_json()) if fig else None
        
        # Lưu log (Thực thi API Logs)
        log_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "prompt": req.prompt,
            "original_code": req.original_code,
            "approved_code": req.approved_code,
            "status": "SUCCESS"
        }
        execution_logs.append(log_entry)
        
        return {"status": "success", "fig_json": fig_json}
    except Exception as e:
        log_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "prompt": req.prompt,
            "approved_code": req.approved_code,
            "status": f"FAILED: {str(e)}"
        }
        execution_logs.append(log_entry)
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/logs")
def get_logs():
    return {"logs": execution_logs}
```

### 2. Code Frontend (Streamlit - `tab_ai.py`)
```python
import streamlit as st
import requests
import plotly.io as pio

API_BASE = "http://localhost:8000/api"

st.title("🤖 Tab 6: Phân Tích Khí Hậu Tích Hợp AI (Human-in-the-Loop)")

tab_studio, tab_logs = st.tabs(["🚀 AI Studio & Code Execution", "📜 Lịch Sử API Logs"])

with tab_studio:
    # 1. Preset Prompts cho buổi Vấn đáp
    st.subheader("💡 Câu hỏi gợi ý (Vấn đáp):")
    cols = st.columns(2)
    preset_prompt = None
    if cols[0].button("1. Tiềm năng Năng lượng Xanh (Nắng + Gió)"):
        preset_prompt = "Vẽ biểu đồ Scatter thể hiện mối quan hệ giữa Bức xạ mặt trời và Tốc độ gió theo 6 vùng khí hậu."
    if cols[1].button("2. Xu hướng biến đổi 35 năm (1991-2025)"):
        preset_prompt = "Vẽ biểu đồ đường Trendline tốc độ gió và bức xạ từ 1991 đến 2025."
        
    user_prompt = st.chat_input("Nhập yêu cầu phân tích...") or preset_prompt

    if user_prompt:
        st.session_state.prompt = user_prompt
        with st.spinner("AI đang tạo mã nguồn phân tích..."):
            res = requests.post(f"{API_BASE}/ai/generate", json={"prompt": user_prompt}).json()
            st.session_state.ai_code = res['code']
            st.session_state.ai_explanation = res['explanation']

    # 2. Trạng thái chờ duyệt
    if 'ai_code' in st.session_state:
        st.markdown("---")
        st.markdown("### 🔍 Giải thích từ AI")
        st.info(st.session_state.ai_explanation)
        
        st.markdown("### ✏️ Xem & Chỉnh sửa Mã Nguồn (Trước khi chạy)")
        edited_code = st.text_area("Bạn có thể sửa tham số code tại đây:", value=st.session_state.ai_code, height=220)
        
        # 3. Chấp nhận & Thực thi
        if st.button("✅ Chấp Nhận & Thực Thi Code", type="primary"):
            with st.spinner("Đang thực thi mã Python local..."):
                payload = {
                    "prompt": st.session_state.prompt,
                    "original_code": st.session_state.ai_code,
                    "approved_code": edited_code
                }
                exec_res = requests.post(f"{API_BASE}/execute", json=payload).json()
                
                if exec_res.get("fig_json"):
                    st.success("Thực thi thành công!")
                    fig = pio.from_json(json.dumps(exec_res["fig_json"]))
                    st.plotly_chart(fig, use_container_width=True)

with tab_logs:
    st.subheader("📜 Nhật ký thực thi (API Logs - Mục 2.2 & 5.2)")
    if st.button("Tải lại Logs"):
        logs = requests.get(f"{API_BASE}/logs").json().get("logs", [])
        st.dataframe(logs)
```