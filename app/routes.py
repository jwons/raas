import shutil
import sys
import os
# For debugging with headless mode-----------
import zipfile
from shutil import copyfile
# -------------------------------------------
from sqlalchemy import desc
from flask import render_template, flash, redirect, url_for, request, jsonify, session
from app import app, db
from app.forms import LoginForm, RegistrationForm, ResetPasswordRequestForm, InputForm
from flask_login import current_user, login_user, login_required, logout_user
from app.models import User, Dataset
from werkzeug.utils import secure_filename
from app.helpers import build_image
from app.starter import start_raas


@app.route('/')
@app.route('/index')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    # get User's dataset with pagination
    datasets = Dataset.query.filter_by(user_id=current_user.id).order_by(desc(Dataset.timestamp)) \
        .paginate(page, 10, False)
    next_url = url_for('index', page=datasets.next_num) if datasets.has_next else None
    prev_url = url_for('index', page=datasets.prev_num) if datasets.has_prev else None
    if datasets.items:
        return render_template('index.html', title='Home', datasets=datasets.items,
                               next_url=next_url, prev_url=prev_url)
    else:
        return render_template('index_new_user.html')


@app.route('/containrize', methods=['GET', 'POST'])
@login_required
def containrize():
    form = InputForm()
    if form.add_pkg.data:
        form.pkg_asked.append_entry()
        return render_template('containrize.html',
                               title='Containrize', form=form, show_adv=True)
    if form.add_cmd.data:
        form.command_line.append_entry()
        return render_template('containrize.html',
                               title='Containrize', form=form, show_adv=True)
    if form.add_code.data:
        form.code_btw.append_entry()
        return render_template('containrize.html',
                               title='Containrize', form=form, show_adv=True)
    # elif form.pkg_asked:
    #     for item in form.pkg_asked:
    #         if item.form.delete.data:
    #             form.pkg_asked.entries.remove(item)
    #             break
    print(form.validate_on_submit())

    if form.validate_on_submit():

        # TODO: support for DOI or other libraries
        # if form.doi.data:
        #     task = build_image.apply_async(kwargs={'current_user_id': current_user.id,
        #                                            'doi': form.doi.data,
        #                                            'name': form.name.data,
        #                                            'preprocess': form.fix_code.data,
        #                                            'dataverse_key': os.environ.get('DATAVERSE_KEY')})
        # else:
        # create directories if they don't exists yet
        if not os.path.exists(app.instance_path):
            os.makedirs(app.instance_path)
        if not os.path.exists(os.path.join(app.instance_path, 'datasets')):
            os.makedirs(os.path.join(app.instance_path, 'datasets'))

        if form.zip_file.data:
            zip_file = form.zip_file.data
            folder_name = secure_filename(form.name.data)
            
#             multi = 0
#             bool_dir = False
#             with zipfile.ZipFile(zip_file, "r") as myzip:
#                 namelist = myzip.infolist()
#                 for i in namelist:
#                     arr = i.filename.split('/')
#                     arr = list(filter(lambda x: x != '', arr))
#                     if (len(arr) == 1):
#                         multi = multi + 1
#                         if (i.is_dir()):
#                             bool_dir = True

#                 file_name = form.zip_file.data.filename
#                 if multi != 1 or not bool_dir:
#                     f_name = file_name[:(file_name.index('.'))]
#                     os.makedirs(os.path.join(app.instance_path, 'datasets', f_name))
#                     myzip.extractall(os.path.join(app.instance_path, 'datasets', f_name))
#                     z = zipfile.ZipFile(os.path.join(app.instance_path, 'datasets', file_name), 'w')
#                     p = os.path.join(app.instance_path, 'datasets', f_name)
#                     for root, dirs, files in os.walk(p):
#                         for file in files:
#                             z.write(os.path.join(root, file),
#                                     os.path.relpath(os.path.join(file), os.path.join(p, '..')))
#                     z.extractall(os.path.join(app.instance_path, 'datasets', folder_name, "data_set_content"))
#                     z.close()

#                     shutil.rmtree(os.path.join(app.instance_path, 'datasets', f_name), ignore_errors=True)
#                 else:
#                     z = zipfile.ZipFile(zip_file)
#                     z.extractall(os.path.join(app.instance_path, 'datasets', folder_name, "data_set_content"))
#                     z.close()
            z = zipfile.ZipFile(zip_file)
            z.extractall(os.path.join(app.instance_path, 'datasets', folder_name, "data_set_content"))
            z.close()        
        else:
            folder_name = secure_filename(form.name.data)
            zipfile_path = os.path.join(app.instance_path, 'datasets', folder_name)
            file_list = request.files.getlist('set_file')
            os.makedirs(zipfile_path)
            os.makedirs(os.path.join(zipfile_path, "data_set_content"))
            for f in file_list:
                f.save(os.path.join(zipfile_path, "data_set_content", f.filename))

        user_pkgs_list = []
        if form.pkg_asked.data:
            for entry in form.pkg_asked.data:
                print(entry)
                temp = {"pkg_name": entry['package_name'], "installation_cmd": entry['installation_cmd']}
                user_pkgs_list.append(temp)
        allinstr = []
        ext_pkgs = []
        for instr in form.command_line.data:
            cur=instr['command']
            if(cur!=""):
                allinstr.append(cur)

        for pkg in form.code_btw.data:
            cur=pkg['code']
            if cur!="":
                ext_pkgs.append(pkg['code'])
        user_pkgs_total = str({"pkg": user_pkgs_list}).replace('\'', '\"')
        print(str(user_pkgs_total))
        # TODO: The backend function will be called here
        print("Language: " + form.language.data)
        if form.language.data == "R":
            task = build_image.apply_async(kwargs={'data_folder': folder_name,
                                                   'current_user_id': current_user.id,
                                                   'name': form.name.data,
                                                   'preprocess': form.fix_code.data})
        else:

            task = start_raas.apply_async(kwargs={'language': form.language.data,
                                                  'data_folder': folder_name,
                                                  'current_user_id': current_user.id,
                                                  'name': form.name.data,
                                                  'preprocess': form.fix_code.data,
                                                  'user_pkgs': user_pkgs_total,
                                                  'run_instr': allinstr,
                                                  'sample_output': '',
                                                  'code_btw': ext_pkgs,
                                                  'prov': ''
                                                  })

        session['task_id'] = task.id
        return redirect(url_for('build_status'))
    return render_template('containrize.html',
                           title='Containrize', form=form, show_adv=False)


@app.route('/build-status', methods=['GET', 'POST'])
@login_required
def build_status():
    task_id = session.get('task_id', None)
    if task_id:
        task_url = url_for('taskstatus', task_id=task_id)
        return render_template('build_status.html', task_url_dict={'task_url': task_url})
    else:
        return render_template('none_building.html')


# provide status information to the front end
@app.route('/status/<task_id>')
def taskstatus(task_id):
    task = build_image.AsyncResult(task_id)
    print(task, file=sys.stderr)
    if task.state == 'PENDING':
        response = {
            'state': task.state,
            'current': 0,
            'total': 1,
            'status': 'Pending...'
        }
    elif task.state != 'FAILURE':
        response = {
            'state': task.state,
            'current': task.info.get('current', 0),
            'total': task.info.get('total', 1),
            'status': task.info.get('status', '')
        }
        if 'result' in task.info:
            response['result'] = task.info['result']
    else:
        # something went wrong in the background job
        response = {
            'state': task.state,
            'current': 1,
            'total': 1,
            'status': str(task.info),  # this is the exception raised
        }
    return jsonify(response)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        return redirect(url_for('index'))
    return render_template('login.html', title='Sign In', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


from app.email_support import send_password_reset_email


@app.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            send_password_reset_email(user)
        flash('Check your email for the instructions to reset your password')
        return redirect(url_for('login'))
    return render_template('reset_password_request.html',
                           title='Password Reset Request', form=form)


from app.forms import ResetPasswordForm


@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    user = User.verify_reset_password_token(token)
    if not user:
        return redirect(url_for('index'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('Your password has been reset.')
        return redirect(url_for('login'))
    return render_template('reset_password.html', form=form, title='Reset Password')


@app.route('/about', methods=['GET', 'POST'])
def about():
    return render_template('about.html', title='About')


@app.route('/instructions', methods=['GET', 'POST'])
def instructions():
    return render_template('instructions.html', title='Instructions')


@app.route('/report', methods=['GET', 'POST'])
def report():
    reportNum = request.args.get('reportNum', None)
    dataset = Dataset.query.get(reportNum)
    if (current_user.id != dataset.user_id):
        return redirect(url_for('index'))
    report = dataset.report
    return render_template('report.html', title='Instructions', report=report)


@app.route('/api/build_image', methods=['GET', 'POST'])
def api_build():
    # Get arguments from url
    user_id = 1
    name = ''
    preprocess = False
    dataverse_key = ''
    doi = ''
    zip_file = ''

    if 'userID' in request.args:
        user_id = int(request.args['userID'])

    if 'name' in request.args:
        name = request.args['name']

    if 'preprocess' in request.args:
        preprocess = bool(int(request.args['preprocess']))

    if 'dataverse_key' in request.args:
        dataverse_key = request.args['dataverse_key']

    if 'doi' in request.args:
        doi = request.args['doi']

    if 'zipFile' in request.args:
        zip_file = request.args['zipFile']

    if doi != '':
        task = build_image.apply_async(kwargs={'current_user_id': user_id,
                                               'doi': doi,
                                               'name': name,
                                               'preprocess': preprocess,
                                               'dataverse_key': os.environ.get('DATAVERSE_KEY')})
    else:
        # create directories if they don't exists yet
        if not os.path.exists(app.instance_path):
            os.makedirs(app.instance_path)
        if not os.path.exists(os.path.join(app.instance_path, 'datasets')):
            os.makedirs(os.path.join(app.instance_path, 'datasets'))
        # save the .zip file to the correct location
        zip_base = os.path.basename(zip_file)
        copyfile(os.path.join(app.instance_path, 'datasets', zip_base), zip_file)

        task = build_image.apply_async(kwargs={'zip_file': zip_base,
                                               'current_user_id': user_id,
                                               'name': name,
                                               'preprocess': preprocess})

    return ("True")
