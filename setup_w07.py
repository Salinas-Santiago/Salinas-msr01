"""Genera vistas, rutas y plantillas de lista/detalle (W07).

Uso (desde C:\\Temp_Workspace_ERP, con el entorno virtual activo):
    python setup_w07.py

Reescribe views.py y urls.py de clientes, productos, proveedores y ventas.
Si ya existian, guarda una copia con extension .bak_w07.
"""
import re
from pathlib import Path

RAIZ = Path.cwd()
if not (RAIZ / 'manage.py').exists():
    raise SystemExit('Ejecuta este script desde la carpeta que contiene manage.py')

# ---------------------------------------------------------------------------
# Detectar el bloque de contenido de templates/base.html
# ---------------------------------------------------------------------------
base = RAIZ / 'templates' / 'base.html'
bloque = None
tiene_title = False
if base.exists():
    txt = base.read_text(encoding='utf-8', errors='replace')
    tiene_title = bool(re.search(r"\{%\s*block\s+title\s*%\}", txt))
    for c in ('content', 'contenido', 'main', 'body'):
        if re.search(r"\{%\s*block\s+" + c + r"\s*%\}", txt):
            bloque = c
            break

if bloque:
    CABECERA = "{% extends 'base.html' %}\n"
    if tiene_title:
        CABECERA += "{% block title %}@TITULO@{% endblock %}\n"
    CABECERA += "{% block " + bloque + " %}\n"
    PIE = "\n{% endblock %}\n"
    print(f"Plantillas extienden base.html (bloque '{bloque}')")
else:
    CABECERA = ("<!doctype html>\n<html lang=\"es\"><head><meta charset=\"utf-8\">"
                "<title>@TITULO@</title></head><body>\n")
    PIE = "\n</body></html>\n"
    print("No encontre un bloque de contenido en base.html: plantillas independientes")


def escribir(ruta, contenido):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    if ruta.exists():
        copia = ruta.with_name(ruta.name + '.bak_w07')
        if not copia.exists():
            copia.write_text(ruta.read_text(encoding='utf-8', errors='replace'),
                             encoding='utf-8')
    ruta.write_text(contenido, encoding='utf-8', newline='\n')
    print('  escrito:', ruta.relative_to(RAIZ))


def plantilla(titulo, cuerpo):
    return (CABECERA + cuerpo + PIE).replace('@TITULO@', titulo)


# ---------------------------------------------------------------------------
# Definicion de las apps
# ---------------------------------------------------------------------------
APPS = [
    dict(app='clientes', M='Cliente', ctx='clientes', single='cliente',
         titulo='Clientes', singular='Cliente',
         campos=[('Nombre', 'nombre'), ('Correo', 'correo')]),
    dict(app='productos', M='Producto', ctx='productos', single='producto',
         titulo='Productos', singular='Producto',
         campos=[('Nombre', 'nombre'), ('Precio', 'precio'),
                 ('Stock', 'stock'), ('Categor&iacute;a', 'categoria')]),
    dict(app='proveedores', M='Proveedor', ctx='proveedores', single='proveedor',
         titulo='Proveedores', singular='Proveedor',
         campos=[('Nombre', 'nombre'), ('Correo', 'correo')]),
    dict(app='ventas', M='Venta', ctx='ventas', single='venta',
         titulo='Ventas', singular='Venta',
         campos=[('N&uacute;mero', 'pk'), ('Cliente', 'cliente')]),
]

VIEWS = '''from django.shortcuts import render
from django.views.generic import DetailView, ListView

from .models import @M@


def index(request):
    return render(request, '@app@/index.html', {})


class @M@ListView(ListView):
    model = @M@
    template_name = '@app@/lista.html'
    context_object_name = '@ctx@'
    paginate_by = 20
    ordering = ['pk']


@DETAIL@
'''

DETAIL_BASICO = '''class @M@DetailView(DetailView):
    model = @M@
    template_name = '@app@/detalle.html'
    context_object_name = '@single@'
'''

VIEWS_VENTAS = '''from decimal import Decimal

from django.shortcuts import render
from django.views.generic import DetailView, ListView

from .models import DetalleVenta, Venta


def index(request):
    return render(request, 'ventas/index.html', {})


class VentaListView(ListView):
    model = Venta
    template_name = 'ventas/lista.html'
    context_object_name = 'ventas'
    paginate_by = 20
    ordering = ['pk']


class VentaDetailView(DetailView):
    model = Venta
    template_name = 'ventas/detalle.html'
    context_object_name = 'venta'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        filas = []
        total = Decimal('0')
        detalles = DetalleVenta.objects.filter(venta=self.object)
        for d in detalles.select_related('producto'):
            subtotal = d.cantidad * d.precio_unitario
            total += subtotal
            filas.append({
                'producto': d.producto,
                'cantidad': d.cantidad,
                'precio_unitario': d.precio_unitario,
                'subtotal': subtotal,
            })
        ctx['filas'] = filas
        ctx['total'] = total
        return ctx
'''

URLS = '''from django.urls import path

from . import views

app_name = '@app@'

urlpatterns = [
    path('', views.index, name='inicio'),
    path('lista/', views.@M@ListView.as_view(), name='lista'),
    path('<int:pk>/', views.@M@DetailView.as_view(), name='detalle'),
]
'''

LISTA = '''<h1>@TITULO@</h1>
<table>
  <thead><tr>@TH@<th></th></tr></thead>
  <tbody>
  {% for o in @ctx@ %}
    <tr>@TD@<td><a href="{% url '@app@:detalle' o.pk %}">Ver</a></td></tr>
  {% empty %}
    <tr><td colspan="@N@">Sin registros.</td></tr>
  {% endfor %}
  </tbody>
</table>
{% if is_paginated %}
<p>
  {% if page_obj.has_previous %}<a href="?page={{ page_obj.previous_page_number }}">Anterior</a>{% endif %}
  P&aacute;gina {{ page_obj.number }} de {{ page_obj.paginator.num_pages }}
  {% if page_obj.has_next %}<a href="?page={{ page_obj.next_page_number }}">Siguiente</a>{% endif %}
</p>
{% endif %}
<p><a href="{% url 'inicio' %}">Inicio</a></p>'''

DETALLE = '''<h1>@SINGULAR@ #{{ @single@.pk }}</h1>
<dl>
@DL@
</dl>
<p><a href="{% url '@app@:lista' %}">Volver a la lista</a></p>'''

DETALLE_VENTA = '''<h1>Venta #{{ venta.pk }}</h1>
<p>Cliente: {{ venta.cliente }}</p>
<table>
  <thead>
    <tr><th>Producto</th><th>Cantidad</th><th>Precio unitario</th><th>Subtotal</th></tr>
  </thead>
  <tbody>
  {% for f in filas %}
    <tr>
      <td>{{ f.producto }}</td>
      <td>{{ f.cantidad }}</td>
      <td>{{ f.precio_unitario|floatformat:"2u" }}</td>
      <td>{{ f.subtotal|floatformat:"2u" }}</td>
    </tr>
  {% endfor %}
  </tbody>
</table>
<p><strong>Total: {{ total|floatformat:"2u" }}</strong></p>
<p><a href="{% url 'ventas:lista' %}">Volver a la lista</a></p>'''


def reemplazar(texto, datos):
    for k, v in datos.items():
        texto = texto.replace('@' + k + '@', v)
    return texto


for a in APPS:
    carpeta = RAIZ / a['app']
    if not carpeta.exists():
        print(f"AVISO: no existe la carpeta {a['app']}, la omito")
        continue
    print(f"\n{a['app']}:")

    datos = dict(app=a['app'], M=a['M'], ctx=a['ctx'], single=a['single'],
                 TITULO=a['titulo'], SINGULAR=a['singular'])

    # views.py
    if a['app'] == 'ventas':
        vistas = VIEWS_VENTAS
    else:
        vistas = VIEWS.replace('@DETAIL@', DETAIL_BASICO)
        vistas = reemplazar(vistas, datos)
    escribir(carpeta / 'views.py', vistas)

    # urls.py
    escribir(carpeta / 'urls.py', reemplazar(URLS, datos))

    # lista.html
    th = ''.join(f'<th>{h}</th>' for h, _ in a['campos'])
    td = ''.join('<td>{{ o.%s }}</td>' % campo for _, campo in a['campos'])
    lista = reemplazar(LISTA, dict(datos, TH=th, TD=td, N=str(len(a['campos']) + 1)))
    escribir(carpeta / 'templates' / a['app'] / 'lista.html',
             plantilla(a['titulo'], lista))

    # detalle.html
    if a['app'] == 'ventas':
        cuerpo = DETALLE_VENTA
    else:
        dl = '\n'.join(
            '  <dt>%s</dt><dd>{{ %s.%s }}</dd>' % (h, a['single'], campo)
            for h, campo in a['campos']
        )
        cuerpo = reemplazar(DETALLE, dict(datos, DL=dl))
    escribir(carpeta / 'templates' / a['app'] / 'detalle.html',
             plantilla(a['singular'], cuerpo))

print('\nListo. Ahora ejecuta:')
print('  python manage.py test tests --verbosity=0')