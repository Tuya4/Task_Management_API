# Task Management API

A Django REST Framework-based Task Management API that allows users to create, update, delete, and manage tasks. The API supports user authentication, task filtering, sharing tasks with other users, and advanced task management features.

## Features

- **User Authentication**: Register, login, logout, and manage users.
- **Task CRUD Operations**: Create, read, update, delete tasks.
- **Task Filtering**: Filter tasks based on status, priority, and due date.
- **Task Sharing**: Share tasks with other users, allowing them to view or edit tasks.
- **Task Status**: Mark tasks as pending or completed.
- **Task Priority**: Assign priorities to tasks (Low, Medium, High).
- **User Permissions**: Control who can view or edit shared tasks.

## Requirements

- Python 3.8+
- Django 4.0+
- Django REST Framework
- PostgreSQL (or any other compatible database)
- Docker (optional, for deployment)

## Setup Instructions

1. **Clone the repository:**

   ```bash
   git clone https://github.com/yourusername/task-management-api.git
   cd task-management-api
   ```

2. **Create a virtual environment:**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. **Install the dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure the environment variables:**

   Create a `.env` file in the project root directory and add your environment variables.

   ```bash
   SECRET_KEY=your_secret_key
   DEBUG=True
   DATABASE_URL=postgres://user:password@localhost:5432/task_management
   ```

5. **Run migrations:**

   ```bash
   python manage.py migrate
   ```

6. **Create a superuser (for admin access):**

   ```bash
   python manage.py createsuperuser
   ```

7. **Run the development server:**

   ```bash
   python manage.py runserver
   ```

   The API should now be available at `http://127.0.0.1:8000/`.

## API Endpoints

### Authentication

- **Register**: `POST /api/register/`
- **Login**: `POST /api/login/`
- **Logout**: `POST /api/logout/`

### Task Management

- **List Tasks**: `GET /api/tasks/`
- **Create Task**: `POST /api/tasks/`
- **Retrieve Task**: `GET /api/tasks/{id}/`
- **Update Task**: `PUT /api/tasks/{id}/`
- **Delete Task**: `DELETE /api/tasks/{id}/`
- **Mark Task as Completed**: `PATCH /api/tasks/{id}/complete/`

### Task Sharing

- **Share Task**: `POST /api/tasks/{id}/share/`
  - **Request Body:**
    ```json
    {
    	"user_id": 2,
    	"can_edit": true
    }
    ```

### Task Filtering

- **Filter Tasks**: `GET /api/tasks/?status=Completed&priority=High&due_date=2024-12-31`

  Example Query Parameters:

  - `status`: Pending, Completed
  - `priority`: Low, Medium, High
  - `due_date`: Exact due date in `YYYY-MM-DD` format
  - `due_date_range`: Tasks due within a date range (requires custom implementation)

## Models

### Task

- **Fields**:
  - `title` (CharField): Title of the task.
  - `description` (TextField): Task description.
  - `status` (CharField): Task status (Pending/Completed).
  - `priority` (CharField): Priority level (Low/Medium/High).
  - `due_date` (DateField): Due date for the task.
  - `created_at` (DateTimeField): Task creation time.
  - `updated_at` (DateTimeField): Last update time.

### SharedTask

- **Fields**:
  - `task` (ForeignKey): The task being shared.
  - `shared_with` (ForeignKey): The user with whom the task is shared.
  - `can_edit` (BooleanField): Whether the user has edit permissions on the task.

## Testing

1. Run the test suite with:

   ```bash
   python manage.py test
   ```

2. Alternatively, you can run specific app tests:

   ```bash
   python manage.py test tasks
   ```

## Deployment

To deploy the API to production (e.g., using Heroku or Docker):

### Heroku

1. Set up a Heroku project and add your environment variables in the dashboard.
2. Push your code to Heroku:

   ```bash
   git push heroku main
   ```

Happy Coding!
