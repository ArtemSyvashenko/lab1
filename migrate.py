import argparse
import pymysql


def main():
    parser = argparse.ArgumentParser(
        description="Database migration script for Task Tracker"
    )
    parser.add_argument("--db-host", default="localhost", help="Database host")
    parser.add_argument(
        "--db-port", type=int, default=3306, help="Database port"
    )
    parser.add_argument("--db-user", default="root", help="Database user")
    parser.add_argument(
        "--db-password", default="", help="Database user password"
    )
    parser.add_argument("--db-name", default="mywebapp", help="Database name")

    args = parser.parse_args()

    print("Connecting to the database...")
    connection = pymysql.connect(
        host=args.db_host,
        port=args.db_port,
        user=args.db_user,
        password=args.db_password,
        database=args.db_name,
        autocommit=True,
    )

    try:
        with connection.cursor() as cursor:
            # Створення таблиці, якщо вона відсутня
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    title VARCHAR(255) NOT NULL,
                    status VARCHAR(50) DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
            )
            print("Migration successful: Table 'tasks' is ready.")
    except Exception as e:
        print(f"Migration failed: {e}")
    finally:
        connection.close()


if __name__ == "__main__":
    main()
