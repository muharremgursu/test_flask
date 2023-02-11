from flask import Flask, render_template, redirect, url_for, session, flash, logging, request

#import email_validator
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps

from wtforms.validators import InputRequired, Email # bu satırı stackoverflow'dan ekledim

##############################################################################
# Login Decorator. (Sadece login olan kullanıcılara gösterilecek sayfalarda @app.route'dan sonra bu deocrator'ı kullanacağız.)
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Bu sayfayı görmek için oturum açmalısınız!', 'warning')
            return redirect(url_for('login'))
    return decorated_function
##############################################################################

# Yeni Kullanıcı Kayıt Formu
class RegisterForm(Form):
    name = StringField("İsim Soyisim", validators=[validators.Length(min=4, max=25)])
    username = StringField("Kullanıcı Adı", validators=[validators.Length(min=5, max=35)])
    email = StringField("E-mail adresiniz", validators=[InputRequired("Please enter your email address."), Email("This field requires a valid email address")])
    password = PasswordField('New Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords must match')
    ])
    confirm = PasswordField('Parola Doğrula')

# Login Formu
class LoginForm(Form):
    username = StringField("Kullanıcı Adı")
    password = PasswordField('Parola')

app = Flask(__name__)

app.secret_key = 'iremgursu'

app.config['MYSQL_HOST'] = "localhost"
app.config['MYSQL_USER'] = "root"
app.config['MYSQL_PASSWORD'] = ""
app.config['MYSQL_DB'] = "ybblog"
app.config['MYSQL_CURSORCLASS'] = "DictCursor"

mysql = MySQL(app)



@app.route("/")
def index():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html', title='Hakkımızda')

@app.route('/articles')
def articles():
    curr = mysql.connection.cursor()
    sorgu = "SELECT * FROM articles"
    result = curr.execute(sorgu)
    if result > 0:
        articles = curr.fetchall()
        return render_template('articles.html', articles=articles)
    else:
        return render_template('articles.html', id=id)

@app.route('/detail/<string:id>')
def detail(id):
    curr = mysql.connection.cursor()
    sorgu = "SELECT * FROM articles WHERE id = %s"
    result = curr.execute(sorgu, (id,))
    if result > 0:
        article = curr.fetchone()
        return render_template('detail.html', article=article)
    else:
        return render_template('detail.html')

# Kullanıcı Kayıt Sayfası
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm(request.form)

    if request.method == 'POST' and form.validate():
        name = form.name.data
        username = form.username.data
        email = form.email.data
        password = sha256_crypt.encrypt(form.password.data)

        curr = mysql.connection.cursor()
        sorgu = "INSERT INTO users(name, email, username, password) VALUES(%s, %s, %s, %s)"
        curr.execute(sorgu, (name, email, username, password))
        mysql.connection.commit()
        curr.close()
        flash('Kayıt oluşturuldu', 'success')
        return redirect(url_for('login'))
    
    else:
        return render_template('register.html', form=form)

# Login Sayfası
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm(request.form)
    
    if request.method == 'POST':
        username = form.username.data
        password_entered = form.password.data
        
        curr = mysql.connection.cursor()
        sorgu = "SELECT * FROM users WHERE username = %s"
        result = curr.execute(sorgu, (username,))
        if result > 0:
            data = curr.fetchone()
            real_password = data['password']
            if sha256_crypt.verify(password_entered, real_password):
                flash('Giriş Başarılı.', 'success')
                session['logged_in'] = True
                session['username'] = username
                return redirect(url_for('index'))
            else:
                flash('Parola hatalı. Tekrar deneyiniz.', 'danger')
                return redirect(url_for('login'))
        else:
            flash('Kullanıcı adı bulunamadı.', "danger")
            return redirect(url_for('login'))
    else:
        return render_template('login.html', form=form)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# KONTROL PANELİ 
@app.route('/dashboard')
@login_required # Bu decorator sayesinde sadece giriş yapan kullanıcılar kontrol panelini görebilecek.
def dashboard():
    curr = mysql.connection.cursor()
    sorgu = "SELECT * FROM articles WHERE author = %s"
    result = curr.execute(sorgu, (session['username'],))
    my_articles = curr.fetchall()    

    return render_template('dashboard.html', my_articles=my_articles, result=result)

# Makale Ekleme
@app.route('/addarticle', methods=['GET', 'POST'])
@login_required
def addarticle():
    form = ArticleForm(request.form)
    if request.method == 'POST' and form.validate():
        title = form.title.data
        content = form.content.data

        curr = mysql.connection.cursor()
        sorgu = "INSERT INTO articles (title, author, content) VALUES(%s, %s, %s)"
        curr.execute(sorgu, (title, session['username'], content))
        mysql.connection.commit()
        curr.close()
        flash('Makale oluşturuldu', 'success')
        return redirect(url_for('addarticle'))

    return render_template("addarticle.html", form=form)

# Makale Silme
@app.route('/delete/<string:id>')
@login_required
def delete(id):
    curr = mysql.connection.cursor()
    sorgu = "SELECT * FROM articles WHERE author = %s and id = %s"
    result = curr.execute(sorgu, (session['username'], id))

    if result > 0:
        sorgu2 = "DELETE FROM articles where id = %s"
        curr.execute(sorgu2, (id,))
        mysql.connection.commit()
        return redirect(url_for('dashboard'))
    else:
        flash('Böyle bir makale yok ya da makaleyi silmek için yetkili değilsiniz', 'danger')
        return redirect(url_for('index'))

# Makaleyi Düzenleme
@app.route('/edit/<string:id>', methods=['GET', 'POST'])
@login_required
def update(id):
    if request.method == 'GET':
        curr = mysql.connection.cursor()
        sorgu = "SELECT * FROM articles WHERE id = %s AND author = %s"
        result = curr.execute(sorgu, (id, session['username']))
        if result == 0:
            flash('Böyle bir makale yok ya da düzenleme yetkiniz yok', 'danger')
            return redirect(url_for('dashboard'))
        else:
            article = curr.fetchone()
            
            form = ArticleForm()
            form.title.data = article['title']
            form.content.data = article['content']
            return render_template('update.html', form=form)
    else:
        form = ArticleForm(request.form)
        new_title = form.title.data
        new_content = form.content.data

        sorgu2 = "UPDATE articles SET title = %s, content = %s WHERE id = %s"
        curr = mysql.connection.cursor()
        curr.execute(sorgu2, (new_title, new_content, id))
        mysql.connection.commit()

        flash('Makale güncellendi.', 'success')
        return redirect(url_for('dashboard'))
    
# Site İçi Makale Arama
@app.route('/search/', methods=['GET', 'POST'])
def search():
    if request.method == 'GET':
        return redirect(url_for('index'))
    else:
        keyword = request.form.get("keyword")

        curr = mysql.connection.cursor()
        sorgu = "SELECT * FROM articles WHERE title LIKE '%" + keyword + "%'"
        result = curr.execute(sorgu)
        if result == 0:
            flash('Aradığınız makaleyi bulamadık.', 'danger')
            return redirect(url_for('articles'))
        else:
            articles = curr.fetchall()
            return render_template('articles.html', articles=articles)



#Makale Formu
class ArticleForm(Form):
    title = StringField('Makale Başlığı', validators=[validators.Length(min=5, max=100)])
    content = TextAreaField('Makale İçeriği', validators=[validators.Length(min=10)])



if __name__ == '__main__':
    app.run(debug=True)