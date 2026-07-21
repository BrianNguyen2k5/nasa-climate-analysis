import os
import re
import json
import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(
    title="NASA Climate AI Assistant API",
    description="Backend API phục vụ Phân tích Khí hậu Tích hợp AI (Human-in-the-Loop & API Logs)",
    version="1.0.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "nasa_power_vietnam_daily_clean.csv"
LOGS_PATH = BASE_DIR / "api" / "logs.json"

REGION_VIETNAMESE = {
    "North West": "Tây Bắc",
    "North East": "Đông Bắc",
    "Red River Delta": "Đồng bằng sông Hồng",
    "North Central": "Bắc Trung Bộ",
    "South Central Coast": "Duyên hải Nam Trung Bộ",
    "Central Highlands": "Tây Nguyên",
}

LOCATION_VIETNAMESE = {
    "Lai Chau": "Lai Châu",
    "Sapa": "Sa Pa",
    "Son La": "Sơn La",
    "Ha Giang": "Hà Giang",
    "Cao Bang": "Cao Bằng",
    "Lang Son": "Lạng Sơn",
    "Ha Noi": "Hà Nội",
    "Hai Phong": "Hải Phòng",
    "Ninh Binh": "Ninh Bình",
    "Thanh Hoa": "Thanh Hóa",
    "Vinh": "Vinh",
    "Hue": "Huế",
    "Da Nang": "Đà Nẵng",
    "Quy Nhon": "Quy Nhơn",
    "Nha Trang": "Nha Trang",
    "Da Lat": "Đà Lạt",
    "Pleiku": "Pleiku",
    "Buon Ma Thuot": "Buôn Ma Thuột",
}


_cached_df: Optional[pd.DataFrame] = None


def load_dataset() -> pd.DataFrame:
    global _cached_df
    if _cached_df is not None:
        return _cached_df

    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Dữ liệu không tồn tại tại: {DATA_PATH}")

    df = pd.read_csv(DATA_PATH, low_memory=False)
    if "region" in df.columns:
        df["region_vn"] = df["region"].map(REGION_VIETNAMESE).fillna(df["region"])
    if "location_name" in df.columns:
        df["location_vn"] = df["location_name"].map(LOCATION_VIETNAMESE).fillna(df["location_name"])
    _cached_df = df
    return _cached_df


def get_dataset_metadata() -> str:
    try:
        df = load_dataset()
        cols = list(df.columns)
        dtypes = {col: str(dtype) for col, dtype in df.dtypes.items()}
        sample = df.head(3).to_dict(orient="records")
        return f"""Dataset columns: {cols}
Data types: {dtypes}
Sample data (3 rows): {json.dumps(sample, ensure_ascii=False, default=str)}"""
    except Exception as e:
        return f"Metadata fallback (Error reading file: {e})"


# Pydantic Schemas
class AIGenerateRequest(BaseModel):
    prompt: str
    context_info: Optional[str] = None


class AIGenerateResponse(BaseModel):
    explanation: str
    code: str


class ExecuteRequest(BaseModel):
    prompt: str
    original_code: str
    approved_code: str


class LogItem(BaseModel):
    timestamp: str
    prompt: str
    original_code: Optional[str] = None
    approved_code: str
    status: str
    error_message: Optional[str] = None


def read_logs_from_file() -> List[Dict[str, Any]]:
    if not LOGS_PATH.exists():
        return []
    try:
        with open(LOGS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def write_log_entry(entry: Dict[str, Any]) -> None:
    logs = read_logs_from_file()
    logs.insert(0, entry)  # Newest first
    LOGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOGS_PATH, "w", encoding="utf-8") as f:
        json.dumps(logs, ensure_ascii=False, indent=2)
        f.write(json.dumps(logs, ensure_ascii=False, indent=2))


# Helper for Gemini Call
def call_gemini_llm(prompt: str) -> AIGenerateResponse:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_gemini_api_key_here":
        # Return intelligent mock responses for key climate questions if API key is not yet set
        return generate_mock_ai_response(prompt)

    try:
        # Try google.genai (new SDK) or google.generativeai (classic SDK)
        import google.genai as genai
        client = genai.Client(api_key=api_key)
        
        system_instruction = f"""Bạn là một chuyên gia phân tích dữ liệu khí hậu và lập trình viên Python senior.
Nhiệm vụ của bạn: Viết mã Python để vẽ biểu đồ tương tác sử dụng Plotly Express (`px`) hoặc Plotly Graph Objects (`go`) dựa trên dữ liệu khí hậu đã được nạp sẵn vào biến DataFrame `df`.

CẤU TRÚC DỮ LIỆU `df`:
{get_dataset_metadata()}

CÁC BIẾN CHÍNH:
- WS10M: Tốc độ gió ở độ cao 10m (m/s)
- PS: Áp suất bề mặt (kPa)
- ALLSKY_SFC_SW_DWN: Bức xạ mặt trời bề mặt (MJ/m^2/day hoặc kWh/m^2/day)
- T2M, T2M_MAX, T2M_MIN: Nhiệt độ trung bình, cực đại, cực tiểu (°C)
- PRECTOTCORR: Lượng mưa (mm/day)
- RH2M: Độ ẩm tương đối (%)
- year: Năm (1991 - 2025)
- month: Tháng (1 - 12)
- region_vn: Tên 6 vùng khí hậu tiếng Việt (Tây Bắc, Đông Bắc, Đồng bằng sông Hồng, Bắc Trung Bộ, Duyên hải Nam Trung Bộ, Tây Nguyên)
- location_vn: Tên các điểm đo tiếng Việt

QUY TẮC BẮT BUỘC KHẮT KHE:
1. TUYỆT ĐỐI KHÔNG tự tạo hay khởi tạo dữ liệu giả lập (KHÔNG viết `df = pd.DataFrame(...)` hay bất kỳ đoạn mã giả lập dữ liệu nào).
2. Biến `df` ĐÃ ĐƯỢC NẠP SẴN toàn bộ dữ liệu CSV thực tế từ máy local. Bạn CHỈ CẦN trực tiếp thao tác trên `df` sẵn có (ví dụ: `df_grouped = df.groupby(...)`).
3. Chỉ trả về code Python sử dụng `px` hoặc `go` và lưu kết quả biểu đồ vào biến `fig`.
4. Không tự bịa số liệu bên ngoài.
5. Phải đảm bảo trả về theo đúng định dạng JSON có 2 key: "explanation" và "code".

Định dạng JSON yêu cầu:
```json
{{
  "explanation": "Giải thích ngắn gọn bằng tiếng Việt các bước code và ý nghĩa phân tích...",
  "code": "# Python code\\nfig = px.scatter(df, ...)"
}}
```"""

        full_prompt = f"{system_instruction}\n\nYêu cầu phân tích của người dùng: {prompt}"
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=full_prompt,
        )
        
        text = response.text
        # Parse JSON output from response
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            data = json.loads(match.group(0))
            return AIGenerateResponse(
                explanation=data.get("explanation", "Giải thích tự động từ AI."),
                code=data.get("code", "# fig = px.scatter(df, ...)"),
            )
        
        # Fallback if raw python returned
        return AIGenerateResponse(
            explanation="Mã nguồn được sinh tự động bởi Gemini API.",
            code=text.strip(),
        )

    except Exception as e:
        # Fallback gracefully if API error occurs
        return generate_mock_ai_response(prompt, note=f"(Lưu ý: Đang chạy chế độ mô phỏng do lỗi API Key: {str(e)})")


def generate_mock_ai_response(prompt: str, note: str = "") -> AIGenerateResponse:
    prompt_lower = prompt.lower()
    
    if "năng lượng xanh" in prompt_lower or "nắng" in prompt_lower or "scatter" in prompt_lower:
        explanation = f"Mã Python này nhóm dữ liệu theo Vùng (`region_vn`), tính Bức xạ mặt trời trung bình (`ALLSKY_SFC_SW_DWN`) và Tốc độ gió (`WS10M`). Sau đó dùng `px.scatter` vẽ biểu đồ phân hóa không gian để tìm ra điểm hot-spot năng lượng xanh. {note}"
        code = """# Gom nhóm dữ liệu theo Vùng khí hậu
df_grouped = df.groupby('region_vn')[['ALLSKY_SFC_SW_DWN', 'WS10M', 'PS']].mean().reset_index()

# Vẽ biểu đồ Scatter Potentially Green Energy (Nắng vs Gió)
fig = px.scatter(
    df_grouped,
    x='ALLSKY_SFC_SW_DWN',
    y='WS10M',
    color='region_vn',
    size='PS',
    text='region_vn',
    title='Phân Hóa Không Gian: Tiềm Năng Năng Lượng Xanh (Bức Xạ vs Gió)',
    labels={
        'ALLSKY_SFC_SW_DWN': 'Bức Xạ Mặt Trời Trung Bình (MJ/m²/ngày)',
        'WS10M': 'Tốc Độ Gió Trung Bình (m/s)',
        'region_vn': 'Vùng Khí Hậu',
        'PS': 'Áp Suất Bề Mặt (kPa)'
    }
)
fig.update_traces(textposition='top center', marker=dict(sizeref=2))
fig.update_layout(template='plotly_white')
"""
    elif "xu hướng" in prompt_lower or "35 năm" in prompt_lower or "trend" in prompt_lower:
        explanation = f"Mã Python này tính trung bình Tốc độ gió (`WS10M`) và Bức xạ mặt trời theo từng năm (`year`) từ 1991 đến 2025, kèm đường xu hướng (Trendline) để phát hiện biến đổi khí hậu dài hạn. {note}"
        code = """# Gom nhóm theo năm
df_year = df.groupby('year')[['WS10M', 'ALLSKY_SFC_SW_DWN']].mean().reset_index()

# Vẽ biểu đồ đường theo thời gian
fig = px.line(
    df_year,
    x='year',
    y=['WS10M', 'ALLSKY_SFC_SW_DWN'],
    markers=True,
    title='Xu Hướng Biến Đổi Tốc Độ Gió & Bức Xạ Mặt Trời (1991 - 2025)',
    labels={'year': 'Năm', 'value': 'Giá Trị Trung Bình', 'variable': 'Yếu Tố Khí Tượng'}
)
fig.update_layout(template='plotly_white')
"""
    elif "mùa" in prompt_lower or "tháng" in prompt_lower or "season" in prompt_lower:
        explanation = f"Mã Python này tính trung bình 12 tháng (`month`) cho Gió và Nắng, chuẩn hóa về khoảng 0-100% để so sánh tính bổ trợ theo mùa giữa Gió mùa và Điện mặt trời. {note}"
        code = """# Gom nhóm theo tháng
df_month = df.groupby('month')[['WS10M', 'ALLSKY_SFC_SW_DWN']].mean().reset_index()

# Chuẩn hóa Min-Max về 0 - 100%
df_month['Wind_Norm'] = (df_month['WS10M'] - df_month['WS10M'].min()) / (df_month['WS10M'].max() - df_month['WS10M'].min()) * 100
df_month['Solar_Norm'] = (df_month['ALLSKY_SFC_SW_DWN'] - df_month['ALLSKY_SFC_SW_DWN'].min()) / (df_month['ALLSKY_SFC_SW_DWN'].max() - df_month['ALLSKY_SFC_SW_DWN'].min()) * 100

fig = px.bar(
    df_month,
    x='month',
    y=['Wind_Norm', 'Solar_Norm'],
    barmode='group',
    title='Tính Bổ Trợ Theo Mùa Giữa Gió & Nắng Qua 12 Tháng (Đã Chuẩn Hóa %)',
    labels={'month': 'Tháng Trong Năm', 'value': 'Mức Độ Tương Đối (%)', 'variable': 'Nguồn Năng Lượng'}
)
fig.update_layout(template='plotly_white')
"""
    elif "tương quan" in prompt_lower or "heatmap" in prompt_lower or "matrix" in prompt_lower:
        explanation = f"Mã Python này tính ma trận tương quan giữa Áp suất, Gió, Bức xạ và Nhiệt độ cực đại, sau đó vẽ Heatmap biểu diễn mối liên hệ nguyên nhân - kết quả. {note}"
        code = """# Chọn các cột số chính
corr_cols = ['PS', 'WS10M', 'ALLSKY_SFC_SW_DWN', 'T2M_MAX', 'PRECTOTCORR', 'RH2M']
available_cols = [c for c in corr_cols if c in df.columns]
corr_matrix = df[available_cols].corr().round(2)

fig = px.imshow(
    corr_matrix,
    text_auto=True,
    aspect="auto",
    color_continuous_scale='RdBu_r',
    title='Ma Trận Tương Quan Giữa Các Yếu Tố Khí Tượng & Thời Tiết Cực Đoan'
)
fig.update_layout(template='plotly_white')
"""
    else:
        explanation = f"Đoạn mã Python mặc định nhóm dữ liệu theo vùng khí hậu và tính toán chỉ số khí tượng trung bình. {note}"
        code = """df_summary = df.groupby('region_vn')[['WS10M', 'ALLSKY_SFC_SW_DWN', 'PS']].mean().reset_index()

fig = px.bar(
    df_summary,
    x='region_vn',
    y='WS10M',
    color='ALLSKY_SFC_SW_DWN',
    title='Tốc Độ Gió & Bức Xạ Mặt Trời Trung Bình Theo Vùng Khí Hậu',
    labels={'region_vn': 'Vùng Khí Hậu', 'WS10M': 'Gió (m/s)', 'ALLSKY_SFC_SW_DWN': 'Bức Xạ (MJ/m²/ngày)'}
)
fig.update_layout(template='plotly_white')
"""
    return AIGenerateResponse(explanation=explanation, code=code)


# Endpoints
@app.get("/")
def root():
    return {"message": "NASA Climate AI Assistant API is running.", "docs": "/docs"}


@app.post("/api/ai/generate", response_model=AIGenerateResponse)
def generate_ai(req: AIGenerateRequest):
    if not req.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt không được để trống.")
    return call_gemini_llm(req.prompt)


@app.post("/api/execute")
def execute_code(req: ExecuteRequest):
    if not req.approved_code.strip():
        raise HTTPException(status_code=400, detail="Mã nguồn phê duyệt không được để trống.")

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        df = load_dataset()

        # Safe execution environment
        safe_globals = {
            "df": df,
            "pd": pd,
            "np": np,
            "px": px,
            "go": go,
            "__builtins__": {
                "__import__": __import__,
                "range": range,
                "len": len,
                "int": int,
                "float": float,
                "str": str,
                "bool": bool,
                "dict": dict,
                "list": list,
                "set": set,
                "min": min,
                "max": max,
                "sum": sum,
                "abs": abs,
                "round": round,
                "print": print,
                "isinstance": isinstance,
            },
        }
        safe_locals = {}

        # Execute code
        exec(req.approved_code, safe_globals, safe_locals)

        # Retrieve figure
        fig = safe_locals.get("fig") or safe_globals.get("fig")

        if fig is None:
            raise ValueError("Mã nguồn thực thi không tạo ra biến `fig` (Plotly Figure).")

        fig_json = json.loads(fig.to_json())

        # Record log
        log_entry = {
            "timestamp": timestamp,
            "prompt": req.prompt,
            "original_code": req.original_code,
            "approved_code": req.approved_code,
            "status": "SUCCESS",
            "error_message": None,
        }
        write_log_entry(log_entry)

        return {"status": "success", "fig_json": fig_json}

    except Exception as e:
        error_msg = str(e)
        log_entry = {
            "timestamp": timestamp,
            "prompt": req.prompt,
            "original_code": req.original_code,
            "approved_code": req.approved_code,
            "status": "FAILED",
            "error_message": error_msg,
        }
        write_log_entry(log_entry)
        raise HTTPException(status_code=400, detail=f"Lỗi khi thực thi mã Python: {error_msg}")


@app.get("/api/logs")
def get_logs():
    return {"logs": read_logs_from_file()}


@app.post("/api/logs")
def add_log(item: LogItem):
    write_log_entry(item.model_dump())
    return {"status": "log saved"}
