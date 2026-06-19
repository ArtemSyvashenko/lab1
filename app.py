import argparse
import sys
from fastapi import FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
import pymysql
import uvicorn

parser = argparse.ArgumentParser(description="mywebapp - Task Tracker Service")
parser.add_argument("--db-host", default="localhost", help="Database host")
parser.add_argument("--db-port", type=int, default=3306, help="Database port")
parser.add_argument("--db-user", default="root", help="Database user")
parser.add_argument("--db-password", default="", help="Database password")
parser.add_argument("--db-name", default="mywebapp", help="Database name")
parser.add_argument(
    "--port", type=int, default=3000, help="Application listen port"
)

if "uvicorn" not in sys.argv[0]:
    args, unknown = parser.parse_known_args()
else:
    args = parser.parse_args([])

app = FastAPI(title="mywebapp")


# Функція для отримання синхронного з'єднання з MariaDB
def get_db_connection():
    return pymysql.connect(
        host=args.db_host,
        port=args.db_port,
        user=args.db_user,
        password=args.db_password,
        database=args.db_name,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )


def determine_content_type(accept: str) -> str:
    if accept and "text/html" in accept:
        return "text/html"
    return "application/json"


@app.get("/health/alive")
def health_alive():
    return Response(content="OK", media_type="text/plain", status_code=200)


@app.get("/health/ready")
def health_ready():
    try:
        conn = get_db_connection()
        conn.ping(reconnect=True)
        conn.close()
        return Response(content="OK", media_type="text/plain", status_code=200)
    except Exception as e:
        return Response(
            content=f"Database connection failed: {str(e)}",
            media_type="text/plain",
            status_code=500,
        )


@app.get("/", response_class=HTMLResponse)
def read_root():
    html_content = """
    <html>
        <head><title>mywebapp - Endpoints</title></head>
        <body>
            <h1>Business Logic Endpoints</h1>
            <ul>
                <li><strong>GET /tasks</strong> - List all tasks</li>
                <li><strong>POST /tasks</strong> - Create a new task (Form parameter: title)</li>
                <li><strong>POST /tasks/&lt;id&gt;/done</strong> - Mark task as done</li>
            </ul>
        </body>
    </html>
    """
    return html_content


@app.get("/tasks")
def get_tasks(accept: str = Header(None)):
    fmt = determine_content_type(accept)

    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, title, status, created_at FROM tasks ORDER BY id DESC"
            )
            tasks = cursor.fetchall()
        conn.close()
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Database error: {str(e)}"
        )

    for t in tasks:
        t["created_at"] = t["created_at"].strftime("%Y-%m-%d %H:%M:%S")

    if fmt == "text/html":
        # Plain HTML таблиця (без стилів та JS)
        rows = ""
        for t in tasks:
            rows += (
                f"<tr>"
                f"<td>{t['id']}</td>"
                f"<td>{t['title']}</td>"
                f"<td>{t['status']}</td>"
                f"<td>{t['created_at']}</td>"
                f"</tr>"
            )

        html = f"""
        <html>
        <head><title>Tasks List</title></head>
        <body>
            <h1>Tasks</h1>
            <table border="1">
                <thead>
                    <tr><th>ID</th><th>Title</th><th>Status</th><th>Created At
                    </th></tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
        </body>
        </html>
        """
        return HTMLResponse(content=html)

    return JSONResponse(content=tasks)


@app.post("/tasks")
async def create_task(request: Request, accept: str = Header(None)):
    fmt = determine_content_type(accept)

    content_type = request.headers.get("content-type", "")
    title = None

    if "application/json" in content_type:
        body = await request.json()
        title = body.get("title")
    else:
        # Для стандартних HTML-форм чи x-www-form-urlencoded
        form_data = await request.form()
        title = form_data.get("title")

    if not title:
        raise HTTPException(
            status_code=400, detail="Missing fields: 'title' is required"
        )

    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO tasks (title, status) VALUES (%s, 'pending')",
                (title,),
            )
            new_id = cursor.lastrowid
            cursor.execute(
                "SELECT id, title, status, created_at FROM tasks WHERE id = %s",
                (new_id,),
            )
            task = cursor.fetchone()
        conn.close()
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Database error: {str(e)}"
        )

    task["created_at"] = task["created_at"].strftime("%Y-%m-%d %H:%M:%S")

    if fmt == "text/html":
        html = f"""
        <html>
        <head><title>Task Created</title></head>
        <body>
            <h1>Task Successfully Created</h1>
            <p><strong>ID:</strong> {task['id']}</p>
            <p><strong>Title:</strong> {task['title']}</p>
            <p><strong>Status:</strong> {task['status']}</p>
            <p><strong>Created At:</strong> {task['created_at']}</p>
            <a href="/tasks">Back to tasks list</a>
        </body>
        </html>
        """
        return HTMLResponse(content=html, status_code=201)

    return JSONResponse(content=task, status_code=201)


@app.post("/tasks/{task_id}/done")
def complete_task(task_id: int, accept: str = Header(None)):
    fmt = determine_content_type(accept)

    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM tasks WHERE id = %s", (task_id,))
            if not cursor.fetchone():
                conn.close()
                raise HTTPException(status_code=404, detail="Task not found")

            cursor.execute(
                "UPDATE tasks SET status = 'done' WHERE id = %s", (task_id,)
            )

            cursor.execute(
                "SELECT id, title, status, created_at FROM tasks WHERE id = %s",
                (task_id,),
            )
            task = cursor.fetchone()
        conn.close()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Database error: {str(e)}"
        )

    task["created_at"] = task["created_at"].strftime("%Y-%m-%d %H:%M:%S")

    if fmt == "text/html":
        html = f"""
        <html>
        <head><title>Task Updated</title></head>
        <body>
            <h1>Task Status Changed to Done</h1>
            <p><strong>ID:</strong> {task['id']}</p>
            <p><strong>Title:</strong> {task['title']}</p>
            <p><strong>Status:</strong> {task['status']}</p>
            <a href="/tasks">Back to tasks list</a>
        </body>
        </html>
        """
        return HTMLResponse(content=html)

    return JSONResponse(content=task)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=args.port)
