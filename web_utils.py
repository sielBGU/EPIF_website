from flask import Flask, render_template, request, redirect, url_for, session
from sqlalchemy import create_engine, text
import secrets
from werkzeug.security import generate_password_hash, check_password_hash

# Define your connection string
connection_string = "mssql+pyodbc://SHIMRIT-DESKTOP/SatPics?driver=ODBC+Driver+17+for+SQL+Server"

# Create an engine
engine = create_engine(connection_string)


def login_check(username, password):
    try:
        with engine.connect() as connection:
            # Fetch password hash from the database for the given username
            query = text("SELECT password_hash FROM Users WHERE username = :username")
            result = connection.execute(query, {"username": username})
            user_row = result.fetchone()

        error = False
        if user_row is None:
            error = True
        else:
            input_password_hash = user_row[0]

            # Check if the provided password matches the hash
            if not check_password_hash(input_password_hash, password):
                error = True

        if error:
            return render_template('welcome_login.html', message='Login failed: Username/Password are incorrect')

        # Fetch the user's role from the database
        user_role = get_user_role(username)

        # Ensure the role exists
        if user_role is None:
            return render_template('welcome_login.html', message='Login failed: Wait for admin approval')

        # Set session variables
        session['username'] = username
        session['user_role'] = user_role

        # Redirect the user based on their role
        return redirect(url_for('load_db_page', user_role=user_role))

    except Exception as e:
        # Log the exception and return a generic failure message
        print(f"Error during login: {e}")
        return render_template('welcome_login.html', message=f'Login failed: {e}')


def get_user_role(username):
    with engine.connect() as connection:
        try:
            query = text("SELECT user_role FROM Users WHERE username = :username")
            result = connection.execute(query, {"username": username})
            user_role = result.fetchone()[0]
            return user_role
        except Exception as e:
            print(e)


def get_exist_or_pending():
    with engine.connect() as connection:
        query_pending = text("SELECT username FROM Users Where user_role IS NULL")
        result_pending = connection.execute(query_pending)
        user_requests_pending = [result[0] for result in result_pending.fetchall()]

        query_exists = text("SELECT username FROM Users Where user_role IS NOT NULL")
        result_exists = connection.execute(query_exists)
        user_requests_exists = [result[0] for result in result_exists.fetchall()]

        return user_requests_exists, user_requests_pending


def handle_user_input(filters):
    query_dict = {}
    for filter in filters:
        query_dict[filter] = request.form.getlist(filter)
    query_dict = {key[:-6]: value for key, value in query_dict.items()}
    for key, value in query_dict.items():
        if key in ['Satellite', 'Sensor', 'GeoZone', 'startDate', 'endDate']:
            query_dict[key] = value[0]  # handle the simple filters

    if query_dict['GeoZone'] == '':  # handle GeoZone filter seperatly (exists even when location wasn't chosen)
        del query_dict['GeoZone']

    if query_dict['startDate'] == '' and query_dict['endDate'] == '':  # lastly, handle calendar filter
        del query_dict['startDate'], query_dict['endDate']
        if query_dict == {}:
            raise ValueError("Please Choose A Filter")
        return query_dict  # some filter was chosen, we handled every filter, exit the function
    elif query_dict['startDate'] != '' and query_dict['endDate'] == '':
        query_dict['endDate'] = '9999-12-31'
    elif query_dict['startDate'] == '' and query_dict['endDate'] != '':
        query_dict['startDate'] = '0000-00-00'

    query_dict['TimeTakenFinal'] = (query_dict['startDate'], query_dict['endDate'])
    del query_dict['startDate'], query_dict['endDate']

    return query_dict  # time query values were handled, exit the function


def register_user(username, password, email):
    try:
        password_hash = generate_password_hash(password)
        with engine.connect() as connection:
            register_query = text(
                f"INSERT INTO Users (username, password_hash, email) "
                f"VALUES ('{username}', '{password_hash}', '{email}')")
            with connection.begin():
                connection.execute(register_query)
        # Use the PRG pattern: Redirect to the login page after successful registration
        return redirect(url_for('welcome_login', message="Registration successful, waiting for approval"))
    except Exception as e:
        print(f"Error during registration: {e}")
        return redirect(url_for('register'))


def approve_user(username, user_role_selected):
    with engine.connect() as connection:
        # Fetch user data from PendingUsers
        update_query = text(f"UPDATE Users SET user_role = '{user_role_selected}' WHERE username = '{username}'")
        with connection.begin():
            connection.execute(update_query)
        print(update_query)

    # Redirect back to the user management page
    print(url_for('load_user_manager_page', user_role='Admin'))
    return redirect(url_for('load_user_manager_page', user_role='Admin'))


def delete_user(username):
    with engine.connect() as connection:
        # Delete the user from PendingUsers
        delete_query = text(f"DELETE FROM Users WHERE username = '{username}'")
        with connection.begin():
            connection.execute(delete_query)
        print(delete_query)
    # Redirect back to the user management page
    return redirect(url_for('load_user_manager_page', user_role='Admin'))


def update_user_role(username, new_role):
    with engine.connect() as connection:
        # Update the user's role in the database
        update_query = text(f"UPDATE Users SET user_role = '{new_role}' WHERE username = '{username}'")
        with connection.begin():
            connection.execute(update_query)

    # Redirect back to the manage users page
    return redirect(url_for('load_user_manager_page', user_role='Admin'))


def get_all_usernames():
    with engine.connect() as connection:
        # Update the user's role in the database
        users_query = text(f'SELECT username FROM Users')
        with connection.begin():
            result = connection.execute(users_query)
            usernames = [username[0] for username in result]
    return usernames
