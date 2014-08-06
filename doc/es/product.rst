#:after:product/product:section:crear-variantes#

Crear un producto con variantes sin procesar
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Un producto con **variantes sin procesar** es un producto que, por cada
variante existe otra igual correspondiente a su versión sin procesar. Ésto es
útil cuando nosotros compramos un producto a nuestros proveedores y vendemos
éste mismo producto después de realizarle algún proceso. Tener dos variantes
nos permite controlar de forma diferenciada los productos procesados de los no
procesados, pero que sean variantes de un mismo producto nos facilita
identificarlos como el mismo producto.

.. view:: product.template_view_form
   :field: main_products
   :domain: [['has_raw_products', '=', 'True']]

Si marcamos el campo |has_raw_products| se nos esconderá la vista habitual de
las variantes del producto apareciendo en su lugar dos listas: |main_products|
y |raw_products|, de las cuales sólo |main_products| es editable.

Cuando añadimos una variante nueva para un producto que |has_raw_products|, al
guardar se creará automáticamente la |raw_product| con el mismo código que la
variante que hemos creado añadiéndole, ai así lo hemos configurado, los
prefijos correspondientes (ver el apartado de
`configuración<configuracion-producto>`).

.. |has_raw_products| field:: product.template/has_raw_products
.. |main_products| field:: product.template/main_products
.. |raw_products| field:: product.template/raw_products
.. |raw_product| field:: product.product/raw_product


.. TODO: configuración

