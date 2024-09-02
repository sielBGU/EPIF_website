import json
from urllib.parse import unquote
from web_utils import *
from db_utils import *

geo_dict = get_geo_dict()

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)


@app.route('/', methods=['POST', 'GET'])
def welcome_login():
    message = request.args.get('message', '')
    action = request.form.get('action')
    if request.method == 'POST' and action == 'login':
        username = request.form['username']
        password = request.form['password']
        return login_check(username, password)
    else:
        return render_template('welcome_login.html', message=message)


@app.route('/register', methods=['POST', 'GET'])
def register():
    # Fetch existing usernames from the database
    usernames = get_all_usernames()

    # If validation passes, proceed with registration
    if request.method == 'POST':
        # Get data from the form
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        # Attempt to register the user
        return register_user(username, password, email)

    else:
        # Handle GET request - render the registration form
        return render_template('register.html', usernames=usernames)


@app.route('/logout', methods=['POST', 'GET'])
def logout():
    session.clear()
    return redirect(url_for('welcome_login'))


@app.route('/access/<user_role>', methods=['POST', 'GET'])
def load_db_page(user_role):
    # Ensure the user is logged in by checking if the session contains a role

    if 'user_role' not in session:
        return redirect(url_for('welcome_login'))

    # Get the role from the session
    session_role = session.get('user_role')
    # Check if the session role matches the requested role (extra safety check)
    if session_role == 'Admin' and user_role == 'Admin':
        return render_template('admin_db_page.html',
                               session=session,
                               geo_dict=geo_dict,
                               message="Welcome, Admin!")
    elif session_role == 'Researcher' and user_role == 'Researcher':
        return render_template('researcher_db_page.html',
                               session=session,
                               geo_dict=geo_dict,
                               message="Welcome, Researcher!")
    else:
        # If the user role doesn't match, redirect back to login
        return redirect(url_for('welcome_login'))


@app.route('/access/<user_role>/submit', methods=['POST', 'GET'])
def submit(user_role):
    # Ensure the user is logged in and has the correct role
    try:
        filters_results = handle_user_input(list(request.form.keys()))
        query_results = get_db_results(filters_results)
        message = None
    except ValueError as e:
        message = str(e).strip()
        query_results = []

    return render_template(f'{user_role}_db_page.html',
                           query_keys=query_keys,
                           query_results=query_results,
                           geo_dict=geo_dict,
                           message=message)


@app.route('/access/<user_role>/manage_users', methods=['POST', 'GET'])
def load_user_manager_page(user_role):
    # Ensure the user is logged in by checking if the session contains a role
    if request.method == 'POST':
        action = request.form.get('action')

        if action:
            username = action.split('_')[1]
            if action.startswith('approve_'):
                user_role_selected = request.form.get('new_user_role')
                return approve_user(username, user_role_selected)

            elif action.startswith('save_'):
                new_user_role = request.form.get(f'new_user_role')
                return update_user_role(username, new_user_role)

            elif action.startswith('deny_') or action.startswith('delete_'):
                return delete_user(username)

    if 'user_role' not in session:
        return redirect(url_for('welcome_login'))

    # Get the role from the session
    session_role = session.get('user_role')
    exists_or_pending = get_exist_or_pending()
    # Get the roles of the existing users
    user_roles = {user: get_user_role(user) for user in exists_or_pending[0]}
    processed_users = {}
    for user, role in user_roles.items():
        processed_users[user] = {
            'admin_selected': 'selected' if role == 'Admin' else '',
            'researcher_selected': 'selected' if role == 'Researcher' else ''
        }

    # Check if the session role matches the requested role
    if session_role == 'Admin' and user_role == 'Admin':
        return render_template('manage_users.html',
                               session=session,
                               user_requests=exists_or_pending,
                               user_roles=processed_users)
    else:
        return redirect(url_for('welcome_login'))


@app.route('/access/<user_role>/<add_edit_entry>', methods=['POST', 'GET'])
def load_editor_mode_page(user_role, add_edit_entry):
    # Ensure the user is logged in by checking if the session contains a role
    if 'user_role' not in session:
        return redirect(url_for('welcome_login'))

    # Get the role from the session
    session_role = session.get('user_role')
    # Check if the session role matches the requested role (extra safety check)
    if session_role == 'Admin' and user_role == 'Admin':
        if add_edit_entry == 'EditEntry':
            row_data_json = request.args.get('rowData')
            # Decode the JSON string back to a Python list
            row_data = json.loads(unquote(row_data_json))
            return render_template('edit_entry.html',
                                   query_keys=query_keys, row_data=row_data,
                                   session=session,
                                   geo_dict=geo_dict,
                                   message="Welcome, Admin[editor]!")
        elif add_edit_entry == 'AddEntry':
            row_data = []
            return render_template('add_entry.html',
                                   query_keys=query_keys, row_data=row_data,
                                   session=session,
                                   geo_dict=geo_dict,
                                   message="Welcome, Admin[adder]!")

    else:
        # If the user role doesn't match, redirect back to login
        return redirect(url_for('welcome_login'))


@app.route('/access/<user_role>/EditEntry/submit', methods=['POST', 'GET'])
@app.route('/access/<user_role>/AddEntry/submit', methods=['POST', 'GET'])
def submit_edit_to_db(user_role):
    # Ensure the user is logged in by checking if the session contains a role
    if 'user_role' not in session:
        return redirect(url_for('welcome_login'))

    # Get the role from the session
    session_role = session.get('user_role')
    # Check if the session role matches the requested role (extra safety check)
    if session_role == 'Admin' and user_role == 'Admin':
        print('submit edit to db')
        return render_template('admin_db_page.html',
                               query_keys=query_keys, row_data=[],
                               session=session,
                               geo_dict=geo_dict,
                               message="Submitted edit to database!")


if __name__ == '__main__':
    app.run(debug=True)
