# Manual Deployment Guide for Render

**First, ensure all the previous code changes (`requirements.txt` and `taxman/settings.py`) are pushed to your Git repository (GitHub, GitLab, etc.).**

---

### Part 1: Create the PostgreSQL Database

1.  From the Render Dashboard, click **New +** and select **PostgreSQL**.
2.  Enter a **Name** for your database (e.g., `taxman-db`).
3.  Ensure the **Region** is set to your preference.
4.  Select a **Plan**. The `Free` plan is sufficient to start.
5.  Click **Create Database**.
6.  Wait for the database status to become "Available". Once it is, find the **"Internal Connection String"** and **copy it**. You will need it in the next part.

---

### Part 2: Create the Web Service

1.  From the dashboard, click **New +** and select **Web Service**.
2.  Connect your Git repository where the project is stored.
3.  On the next screen, give your service a **Name** (e.g., `taxman-web`).
4.  Set the **Region** (ideally the same as your database).
5.  The **Branch** should be your main development branch (e.g., `main` or `master`).
6.  Set the **Runtime** to `Python`.
7.  Set the **Build Command** to: `pip install -r requirements.txt && python manage.py collectstatic --no-input && python manage.py migrate`
8.  Set the **Start Command** to: `gunicorn taxman.wsgi:application`
9.  Select an **Instance Type**. The `Free` plan is fine for now.
10. Go to the **"Environment"** section and click **"Add Environment Variable"** to create the following variables:
    *   **Variable 1 (Set Python Version):**
        *   **Key:** `PYTHON_VERSION`
        *   **Value:** `3.11.4` (or the version in your `runtime.txt`)
    *   **Variable 2 (Link Database):**
        *   **Key:** `DATABASE_URL`
        *   **Value:** Paste the **Internal Connection String** you copied from your database service.
    *   **Variable 3 (Set Secret Key):**
        *   **Key:** `SECRET_KEY`
        *   **Value:** Click the `Generate` button to have Render create a secure random value for you.
    *   **Variable 4 (Set Allowed Hosts):**
        *   **Key:** `ALLOWED_HOSTS`
        *   **Value:** Enter the domain of your new web service, which will look something like `taxman-web.onrender.com`. You can also just put `.onrender.com` to be safe.

11. Click **Create Web Service**.

Render will now pull your code, install the dependencies, run the build and start commands, and launch your application. You can monitor the progress in the "Deploy" logs.
