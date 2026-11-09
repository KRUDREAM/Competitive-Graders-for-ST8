from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import subprocess
import os
import time

app = FastAPI(title="Mini C++ Grader Backend")

# เปิดให้ Frontend เรียกใช้งาน API ได้
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SubmissionRequest(BaseModel):
    source_code: str
    language: str = "cpp"
    # ตัวอย่างเทสเคสจำลอง (ปกติจะดึงมาจากฐานข้อมูลหรือไฟล์ .in/.out)
    testcases: list = [
        {"input": "5 10\n", "output": "15\n"},
        {"input": "100 200\n", "output": "300\n"}
    ]

@app.post("/submit")
async def evaluate_code(sub: SubmissionRequest):
    source_ext = "cpp" if sub.language == "cpp" else "c"
    source_file = f"solution.{source_ext}"
    executable_file = "solution_exec"

    # 1. เขียนโค้ดลงไฟล์ชั่วคราว
    with open(source_file, "w") as f:
        f.write(sub.source_code)

    try:
        # 2. Compile โค้ด C/C++ ด้วย g++
        compile_res = subprocess.run(
            ["g++", "-O3", source_file, "-o", executable_file],
            capture_output=True, text=True
        )
        if compile_res.returncode != 0:
            return {
                "verdict": "Compilation Error (CE)",
                "details": compile_res.stderr
            }

        # 3. วนลูปตรวจทีละ Testcase
        total_score = 0
        score_per_tc = 100 / len(sub.testcases) if sub.testcases else 100

        for i, tc in enumerate(sub.testcases):
            start_time = time.time()
            try:
                run_res = subprocess.run(
                    [f"./{executable_file}"],
                    input=tc["input"],
                    text=True,
                    capture_output=True,
                    timeout=1.0 # กำหนด Time Limit 1 วินาที
                )
                exec_time = time.time() - start_time

                if run_res.returncode != 0:
                    return {"verdict": f"Runtime Error (RE) on Testcase {i+1}"}

                # เปรียบเทียบ Output (ตัดช่องว่างหัวท้ายเพื่อความยืดหยุ่น)
                user_out = run_res.stdout.strip().replace("\r\n", "\n")
                expected_out = tc["output"].strip().replace("\r\n", "\n")

                if user_out != expected_out:
                    return {
                        "verdict": f"Wrong Answer (WA) on Testcase {i+1}",
                        "expected": expected_out,
                        "received": user_out
                    }

                total_score += score_per_tc

            except subprocess.TimeoutExpired:
                return {"verdict": f"Time Limit Exceeded (TLE) on Testcase {i+1}"}

        return {
            "verdict": "Accepted (AC)",
            "score": int(total_score)
        }

    finally:
        # ลบไฟล์ชั่วคราวทิ้งหลังตรวจเสร็จเพื่อความสะอาดของระบบ
        if os.path.exists(source_file): os.remove(source_file)
        if os.path.exists(executable_file): os.remove(executable_file)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
