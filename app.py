from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'chave_diamond'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db = SQLAlchemy(app)

class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True)
    password_hash = db.Column(db.String(150))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Servico(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100))
    preco = db.Column(db.Float)

class Pedido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cliente = db.Column(db.String(100))
    modelo = db.Column(db.String(100))
    servico = db.Column(db.String(100))
    imei = db.Column(db.String(100))
    descricao = db.Column(db.Text)
    contato = db.Column(db.String(100))
    status = db.Column(db.String(50), default='Pendente')
    pago = db.Column(db.Boolean, default=False)

class Config(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    regras = db.Column(db.Text)
    contato_empresa = db.Column(db.Text)
    chave_pix = db.Column(db.String(255))

VISITORS = set()

@app.route('/')
def index():
    ip = request.remote_addr
    if ip not in VISITORS:
        VISITORS.add(ip)
    config = Config.query.first()
    return render_template('index.html',
                           servicos=Servico.query.all(),
                           regras=(config.regras if config else ''),
                           contato_empresa=(config.contato_empresa if config else ''),
                           visitas=len(VISITORS))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = Admin.query.filter_by(username=request.form['username']).first()
        if user and user.check_password(request.form['password']):
            session['admin'] = user.username
            return redirect(url_for('admin'))
        flash('Login inválido.')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('index'))

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if 'admin' not in session:
        return redirect(url_for('login'))

    config = Config.query.first()
    if not config:
        config = Config()
        db.session.add(config)

    if request.method == 'POST':
        config.regras = request.form.get("regras")
        config.contato_empresa = request.form.get("contato")
        config.chave_pix = request.form.get("chave_pix")
        db.session.commit()

    pedidos = Pedido.query.all()
    return render_template('admin.html',
                           pedidos=pedidos,
                           servicos=Servico.query.all(),
                           visitas=len(VISITORS),
                           config=config)

@app.route('/add-servico', methods=['POST'])
def add_servico():
    if 'admin' not in session:
        return redirect(url_for('login'))
    nome = request.form.get("nome")
    preco = request.form.get("preco")
    db.session.add(Servico(nome=nome, preco=float(preco)))
    db.session.commit()
    return redirect(url_for('admin'))

@app.route('/remover-servico/<int:id>', methods=['POST'])
def remover_servico(id):
    if 'admin' not in session:
        return redirect(url_for('login'))
    s = Servico.query.get(id)
    if s:
        db.session.delete(s)
        db.session.commit()
    return redirect(url_for('admin'))

@app.route('/remover_pedido/<int:pedido_id>', methods=['POST'])
def remover_pedido(pedido_id):
    if 'admin' not in session:
        flash('Você precisa estar logado para remover pedidos.', 'danger')
        return redirect(url_for('login'))

    pedido = Pedido.query.get_or_404(pedido_id)

    try:
        db.session.delete(pedido)
        db.session.commit()
        flash('Pedido removido com sucesso.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao remover pedido: {str(e)}', 'danger')

    return redirect(url_for('admin'))

@app.route('/pagar/<int:id>')
def pagar(id):
    if 'admin' not in session:
        return redirect(url_for('login'))
    p = Pedido.query.get(id)
    if p:
        p.pago = True
        db.session.commit()
    return redirect(url_for('admin'))

@app.route('/concluir/<int:id>')
def concluir(id):
    if 'admin' not in session:
        return redirect(url_for('login'))
    p = Pedido.query.get(id)
    if p:
        p.status = 'Concluído'
        db.session.commit()
    return redirect(url_for('admin'))

@app.route('/pagamento')
def pagamento():
    config = Config.query.first()
    pedido = Pedido.query.order_by(Pedido.id.desc()).first()
    return render_template('pagamento.html',
                           chave_pix=(config.chave_pix if config else ''),
                           pedido=pedido or {})

@app.route('/enviar', methods=['POST'])
def enviar():
    pedido = Pedido(
        cliente=request.form.get("nome"),
        modelo=request.form.get("modelo"),
        servico=request.form.get("servico"),
        imei=request.form.get("imei"),
        descricao=request.form.get("descricao"),
        contato=request.form.get("contato")
    )
    db.session.add(pedido)
    db.session.commit()
    flash("Requisição enviada com sucesso!")
    return redirect(url_for('pagamento'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not Admin.query.filter_by(username='admin').first():
            a = Admin(username='admin')
            a.set_password('senha123')
            db.session.add(a)
            db.session.commit()

    app.run(debug=True)
