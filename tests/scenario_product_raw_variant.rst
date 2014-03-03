============================
Product Raw Variant Scenario
============================

Imports::

    >>> from decimal import Decimal
    >>> from proteus import config, Model, Wizard

Create database::

    >>> config = config.set_trytond()
    >>> config.pool.test = True

Install product_raw_variant::

    >>> Module = Model.get('ir.module.module')
    >>> raw_variant_module, = Module.find([
    ...         ('name', '=', 'product_raw_variant'),
    ...         ])
    >>> Module.install([raw_variant_module.id], config.context)
    >>> Wizard('ir.module.module.install_upgrade').execute('upgrade')

Create category::

    >>> ProductCategory = Model.get('product.category')
    >>> category = ProductCategory(name='Category')
    >>> category.save()

Create product::

    >>> ProductUom = Model.get('product.uom')
    >>> unit, = ProductUom.find([('name', '=', 'Unit')])
    >>> ProductTemplate = Model.get('product.template')
    >>> template = ProductTemplate()
    >>> template.name = 'Tryton T-Shirt'
    >>> template.category = category
    >>> template.default_uom = unit
    >>> template.type = 'goods'
    >>> template.list_price = Decimal('10')
    >>> template.cost_price = Decimal('5')
    >>> template.cost_price_method = 'fixed'
    >>> import sys
    >>> print >> sys.stderr, "t.list_price:", template.list_price
    >>> print >> sys.stderr, "t.cost_price:", template.cost_price
    >>> template.save()

Create variant without Raw Product::

    >>> Product = Model.get('product.product')
    >>> product = Product()
    >>> product.template = template
    >>> product.save()
    >>> products = Product.find([('template', '=', template.id)])
    >>> len(products)
    2
    >>> main_product = raw_product = None
    >>> for p in products:
    ...     if p.is_raw_product:
    ...         raw_product = p
    ...     else:
    ...         main_product = p
    >>> main_product and main_product.raw_product != None
    True
    >>> raw_product and main_product.raw_product == raw_product
    True
