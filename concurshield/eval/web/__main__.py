"""允许 python -m eval.web 直接启动仪表盘。"""

if __name__ == "__main__":
    import uvicorn
    from eval.web.server import app
    uvicorn.run(app, host="0.0.0.0", port=8501)
