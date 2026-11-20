"""User account routes; legacy file administrators remain independent recovery access."""
from contextlib import closing
import secrets
import sqlite3
from flask import Blueprint,abort,current_app,flash,g,redirect,render_template,request,session,url_for
from .passwords import check_password_hash
from .auth import roles_required
from .database import connect,insert_security_event
from . import account_store as store
from werkzeug.exceptions import HTTPException

bp=Blueprint('accounts',__name__)
GENERIC_RESET='Nếu thông tin phù hợp, hướng dẫn khôi phục sẽ được gửi đến email đăng ký.'


@bp.errorhandler(HTTPException)
def account_error(error):
    messages={400:'Biểu mẫu hoặc tham số không hợp lệ.',403:'Bạn không được phép thực hiện thao tác này.',
              404:'Không tìm thấy tài nguyên.',409:'Thao tác xung đột với chính sách bảo vệ tài khoản quản trị.',429:'Thử quá nhiều lần. Vui lòng thử lại sau.'}
    return render_template('error.html',code=error.code,message=messages.get(error.code,'Không thể hoàn tất thao tác.')),error.code,({'Retry-After':'300'} if error.code==429 else {})


def dbpath():return current_app.config['DATABASE']
def ip():return request.remote_addr or 'unknown'
def rate(scope,value,limit,seconds):return store.take_rate(dbpath(),scope,value,limit,seconds)
def event(name):insert_security_event(dbpath(),ip(),session.get('role','anonymous'),name)


@bp.route('/register',methods=['GET','POST'])
def register():
    error=None
    if request.method=='POST':
        if not rate('register_ip',ip(),current_app.config['ACCOUNT_REGISTER_LIMIT'],3600) or not rate('register_global','all',200,3600):
            event('registration_throttled');return render_template('register.html',error='Thử đăng ký quá nhiều lần. Vui lòng thử lại sau.'),429
        if any(k in request.form for k in ('role','active','user_id')):
            event('registration_privilege_rejected');abort(400)
        password=request.form.get('password','')
        try:
            if password!=request.form.get('confirm_password'):raise ValueError('confirmation')
            store.register(dbpath(),request.form.get('username',''),request.form.get('email',''),request.form.get('display_name',''),password,ip())
        except ValueError:
            error='Username 3–32 ký tự a–z, số, dấu . _ -; email hợp lệ; mật khẩu 6–128 ký tự và xác nhận phải trùng.'
        except sqlite3.IntegrityError:
            # Same response as success, no identifier enumeration or role assignment.
            pass
        if not error:
            flash('Yêu cầu đăng ký đã xử lý. Nếu thông tin phù hợp, bạn có thể đăng nhập.','success')
            return redirect(url_for('login'))
    return render_template('register.html',error=error),400 if error else 200


@bp.route('/forgot-password',methods=['GET','POST'])
def forgot_password():
    if request.method=='POST':
        identifier=request.form.get('identifier','')[:254]
        allowed=rate('reset_ip',ip(),5,900) and rate('reset_identity',store.identity(identifier),3,900) and rate('reset_global','all',60,3600)
        mail=current_app.extensions['recovery_mail']
        if allowed and mail.configured:
            issued=store.issue_reset(dbpath(),identifier,ip())
            if issued:
                address,token,digest=issued
                if not mail.submit(address,token,digest):
                    with closing(connect(dbpath())) as db,db:db.execute('UPDATE auth_reset_tokens SET used=1 WHERE digest=?',(digest,))
        else:event('password_reset_requested')
        return render_template('forgot_password.html',message=GENERIC_RESET)
    return render_template('forgot_password.html')


@bp.route('/reset-password',methods=['GET','POST'])
def reset_password():
    error=None
    if request.method=='POST':
        if not rate('reset_submit',ip(),10,900):return render_template('reset_password.html',error='Thử quá nhiều lần. Vui lòng thử lại sau.'),429
        new=request.form.get('new_password','')
        try:
            if new!=request.form.get('confirm_password'):raise ValueError('confirmation')
            valid=store.reset_password(dbpath(),request.form.get('token',''),new,ip())
        except ValueError:valid=False
        if valid:
            session.clear();flash('Đã đặt lại mật khẩu. Vui lòng đăng nhập lại.','success');return redirect(url_for('login'))
        event('password_reset_failed')
        error='Không thể đặt lại mật khẩu. Liên kết không hợp lệ, đã dùng hoặc hết hạn; kiểm tra mật khẩu và mở lại liên kết email.'
    return render_template('reset_password.html',error=error),400 if error else 200


@bp.route('/account',methods=['GET','POST'])
@roles_required('admin','auditor','user')
def profile():
    account=getattr(g,'account',None);error=None
    if request.method=='POST':
        if not account:abort(403)
        if any(k in request.form for k in ('role','active','user_id','email','username')):abort(400)
        if not rate('profile',str(account['id']),10,300):abort(429)
        try:name=store.display(request.form.get('display_name',''))
        except ValueError:error='Tên hiển thị cần 1–100 ký tự, không chứa ký tự điều khiển.'
        if not error:
            with closing(connect(dbpath())) as db,db:
                changed=db.execute('UPDATE auth_users SET display_name=?,updated_at=? WHERE id=? AND session_version=? AND active=1',(name,store.stamp(),account['id'],account['session_version']))
                if not changed.rowcount:abort(403)
                store.audit(db,ip(),account['role'],'profile_updated:'+str(account['id']))
            return redirect(url_for('accounts.profile'))
    public={k:account[k] for k in ('id','username','email','display_name','role','created_at')} if account else None
    return render_template('account.html',account=public,error=error,mail_configured=current_app.extensions['recovery_mail'].configured),400 if error else 200


def change_password():
    account=getattr(g,'account',None)
    if not account:abort(403)
    error=None;status=200
    if request.method=='POST':
        if not rate('change_password',str(account['id'])+':'+ip(),5,300):return render_template('change_password.html',error='Thử quá nhiều lần. Vui lòng thử lại sau.'),429
        current=request.form.get('current_password','');new=request.form.get('new_password','')
        if len(current)>128 or not check_password_hash(account['password_hash'],current):error='Mật khẩu hiện tại không đúng.';status=403
        elif not 6<=len(new)<=128 or new!=request.form.get('confirm_password') or new==current:error='Mật khẩu mới cần 6–128 ký tự, khác mật khẩu cũ và xác nhận trùng khớp.';status=400
        hashed=store.password_hash(new) if not error else None
        with closing(connect(dbpath())) as db,db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT * FROM auth_users WHERE id=?',(account['id'],)).fetchone()
            if not row or row['session_version']!=account['session_version'] or not row['active']:abort(403)
            if error:store.audit(db,ip(),row['role'],'account_password_change_failed:'+str(row['id']))
            else:
                db.execute('UPDATE auth_users SET password_hash=?,session_version=?,updated_at=? WHERE id=?',(hashed,secrets.token_urlsafe(32),store.stamp(),row['id']))
                db.execute('UPDATE auth_reset_tokens SET used=1 WHERE user_id=?',(row['id'],))
                store.revoke_user_sessions(db,row['id'])
                store.audit(db,ip(),row['role'],'account_password_change_success:'+str(row['id']))
        if not error:
            session.clear();flash('Đổi mật khẩu thành công. Vui lòng đăng nhập lại.','success');return redirect(url_for('login'))
    return render_template('change_password.html',error=error),status


@bp.route('/admin/accounts',methods=['GET','POST'])
@roles_required('admin')
def manage():
    error=None;status=200
    if request.method=='POST':
        if not rate('admin_accounts',ip(),10,60):abort(429)
        account=getattr(g,'account',None)
        current_hash=account['password_hash'] if account else current_app.extensions['credentials'].current('admin')
        supplied=request.form.get('current_password','')
        if len(supplied)>128 or not check_password_hash(current_hash,supplied):
            event('account_admin_reauth_failed');error='Không xác minh được thao tác quản trị.';status=403
        else:
            try:target=int(request.form.get('user_id',''))
            except ValueError:abort(400)
            if not 0<target<=9223372036854775807:abort(400)
            action=request.form.get('action');role=request.form.get('role')
            if action not in {'lock','unlock','role'} or (action=='role' and role not in {'admin','auditor','user'}):abort(400)
            with closing(connect(dbpath())) as db,db:
                db.execute('BEGIN IMMEDIATE')
                if account:
                    actor=db.execute('SELECT role,active,session_version FROM auth_users WHERE id=?',(account['id'],)).fetchone()
                    if not actor or not actor['active'] or actor['role']!='admin' or actor['session_version']!=account['session_version']:abort(403)
                row=db.execute('SELECT * FROM auth_users WHERE id=?',(target,)).fetchone()
                if row is None:abort(404)
                if account and target==account['id']:abort(409)
                if row['role']=='admin' and row['active'] and (action=='lock' or (action=='role' and role!='admin')):
                    if db.execute("SELECT COUNT(*) FROM auth_users WHERE role='admin' AND active=1").fetchone()[0]<=1:abort(409)
                if action=='role':db.execute('UPDATE auth_users SET role=?,session_version=?,updated_at=? WHERE id=?',(role,secrets.token_urlsafe(32),store.stamp(),target))
                else:db.execute('UPDATE auth_users SET active=?,session_version=?,updated_at=? WHERE id=?',(int(action=='unlock'),secrets.token_urlsafe(32),store.stamp(),target))
                db.execute('UPDATE auth_reset_tokens SET used=1 WHERE user_id=?',(target,))
                store.revoke_user_sessions(db,target)
                store.audit(db,ip(),'admin','account_admin_'+action+':'+str(target))
            return redirect(url_for('accounts.manage'))
    role=request.args.get('role','');active=request.args.get('active','');q=request.args.get('q','').strip()[:100]
    if role not in {'','admin','auditor','user'} or active not in {'','0','1'}:abort(400)
    try:page=int(request.args.get('page','1'))
    except ValueError:abort(400)
    if not 1<=page<=1000000:abort(400)
    clauses=[];args=[]
    for column,value in [('role',role),('active',active)]:
        if value!='':clauses.append(column+'=?');args.append(value)
    if q:
        clauses.append("(username LIKE ? ESCAPE '\\' OR email LIKE ? ESCAPE '\\')")
        escaped=q.replace('\\','\\\\').replace('%','\\%').replace('_','\\_');args.extend(['%'+escaped+'%']*2)
    where=' WHERE '+' AND '.join(clauses) if clauses else ''
    with closing(connect(dbpath())) as db:
        total=db.execute('SELECT COUNT(*) FROM auth_users'+where,args).fetchone()[0]
        rows=[dict(r) for r in db.execute('SELECT id,username,email,display_name,role,active FROM auth_users'+where+' ORDER BY id DESC LIMIT 50 OFFSET ?',args+[(page-1)*50])]
    return render_template('accounts_manage.html',users=rows,total=total,page=page,role=role,active=active,q=q,error=error),status
