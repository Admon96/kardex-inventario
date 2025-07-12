import json
import os
from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta_aqui'

# Usuarios y roles ejemplo (puedes cambiar o agregar usuarios)
USUARIOS = {
    'admin': {'password': 'aged123', 'role': 'admin'},
    'user': {'password': '1234', 'role': 'viewer'}
}

PRODUCTOS_FILE = 'productos.json'
MOVIMIENTOS_FILE = 'movimientos.json'

def cargar_productos():
    if not os.path.exists(PRODUCTOS_FILE):
        return []
    try:
        with open(PRODUCTOS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

def guardar_productos(productos):
    with open(PRODUCTOS_FILE, 'w', encoding='utf-8') as f:
        json.dump(productos, f, indent=4)

def cargar_movimientos():
    if not os.path.exists(MOVIMIENTOS_FILE):
        return []
    try:
        with open(MOVIMIENTOS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

def guardar_movimientos(movimientos):
    with open(MOVIMIENTOS_FILE, 'w', encoding='utf-8') as f:
        json.dump(movimientos, f, indent=4)

def calcular_existencia(producto_id):
    movimientos = cargar_movimientos()
    entradas = sum(m['cantidad'] for m in movimientos if m['producto_id'] == producto_id and m['tipo'] == 'entrada')
    salidas = sum(m['cantidad'] for m in movimientos if m['producto_id'] == producto_id and m['tipo'] == 'salida')
    return entradas - salidas

@app.route('/')
def home():
    if 'user' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = ''
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in USUARIOS and USUARIOS[username]['password'] == password:
            session['user'] = username
            session['role'] = USUARIOS[username]['role']
            return redirect(url_for('dashboard'))
        else:
            error = 'Usuario o contraseña incorrectos'
    return render_template('login.html', error=error)

@app.route('/dashboard')
def dashboard():
    if 'user' not in session or 'role' not in session:
        return redirect(url_for('login'))

    productos = cargar_productos()
    movimientos = cargar_movimientos()

    for p in productos:
        p['existencia'] = calcular_existencia(p['id'])
        p['entradas'] = sum(m['cantidad'] for m in movimientos if m['producto_id'] == p['id'] and m['tipo'] == 'entrada')
        p['salidas'] = sum(m['cantidad'] for m in movimientos if m['producto_id'] == p['id'] and m['tipo'] == 'salida')
        p['costo_total'] = p['entradas'] * p['precio']  # Mantener costo según entradas

    materiales = [p for p in productos if p['categoria'] == 'material']
    herramientas = [p for p in productos if p['categoria'] == 'herramienta']
    equipos = [p for p in productos if p['categoria'] == 'equipo']

    total_materiales = sum(p['costo_total'] for p in materiales)

    return render_template('dashboard.html',
                           user=session['user'],
                           role=session['role'],
                           materiales=materiales,
                           herramientas=herramientas,
                           equipos=equipos,
                           total_materiales=total_materiales)

@app.route('/agregar_producto', methods=['POST'])
def agregar_producto():
    if 'user' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    productos = cargar_productos()

    # Asignar nuevo ID secuencial según categoría
    categoria = request.form['categoria']
    prefijo = ''
    if categoria == 'material':
        prefijo = 'MAT'
    elif categoria == 'herramienta':
        prefijo = 'HER'
    elif categoria == 'equipo':
        prefijo = 'EQ'

    # Extraer números de IDs existentes en esa categoría para secuencia
    ids_categoria = [p['id'] for p in productos if p['categoria'] == categoria and p['id'].startswith(prefijo)]
    numeros = [int(id_[len(prefijo):]) for id_ in ids_categoria if id_[len(prefijo):].isdigit()]
    nuevo_num = max(numeros) + 1 if numeros else 1
    nuevo_id = f"{prefijo}{nuevo_num:04d}"

    nuevo_producto = {
        'id': nuevo_id,
        'nombre': request.form['nombre'],
        'precio': float(request.form['precio']),
        'categoria': categoria,
        'unidad': request.form.get('unidad', '')
    }
    productos.append(nuevo_producto)
    guardar_productos(productos)
    return redirect(url_for('dashboard'))

@app.route('/agregar_movimiento/<prod_id>', methods=['POST'])
def agregar_movimiento(prod_id):
    if 'user' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    productos = cargar_productos()
    producto = next((p for p in productos if p['id'] == prod_id), None)
    if not producto:
        return "Producto no encontrado", 404

    tipo = request.form['tipo']
    cantidad = int(request.form['cantidad'])
    existencia_actual = calcular_existencia(prod_id)

    if tipo == 'salida' and cantidad > existencia_actual:
        return f"No hay suficiente existencia. Actual: {existencia_actual}", 400

    movimientos = cargar_movimientos()
    movimientos.append({
        'producto_id': prod_id,
        'tipo': tipo,
        'cantidad': cantidad
    })
    guardar_movimientos(movimientos)

    return redirect(url_for('dashboard'))

@app.route('/eliminar_producto/<prod_id>', methods=['POST'])
def eliminar_producto(prod_id):
    if 'user' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    productos = cargar_productos()
    productos = [p for p in productos if p['id'] != prod_id]
    guardar_productos(productos)
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)

