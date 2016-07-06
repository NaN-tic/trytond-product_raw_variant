# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
import logging
from itertools import izip

from trytond.model import ModelSQL, fields, Unique
from trytond.pool import Pool, PoolMeta
from trytond.pyson import And, Bool, Eval, Or
from trytond.transaction import Transaction

__all__ = ['Configuration', 'Template', 'Product', 'ProductRawProduct']
__metaclass__ = PoolMeta

STATES = {
    'readonly': ~Eval('active', True),
    'invisible': ~Eval('has_raw_products', False),
    }
DEPENDS = ['active', 'has_raw_products']


class Configuration:
    __name__ = 'product.configuration'
    raw_product_prefix = fields.Char('Raw variant prefix',
        help='This prefix will be added to raw variant code')
    main_product_prefix = fields.Char('Main variant prefix',
        help='This prefix will be added to main variant code')


class Template:
    __name__ = 'product.template'

    has_raw_products = fields.Boolean('Has Raw Variants',
        help='If you check this option, all variants must to have one and '
        'only one raw variant.\n'
        'The system will create it when a variant is created.')
    main_products = fields.Function(fields.One2Many('product.product',
            'template', 'Main Variants', domain=[
                ('is_raw_product', '=', False),
                ], states=STATES, depends=DEPENDS, context={
                'no_create_raw_products': True,
                }),
        'get_main_products', setter='set_main_products')
    raw_products = fields.Function(fields.One2Many('product.product',
            'template', 'Raw Variants', domain=[
                ('is_raw_product', '=', True),
                ], states=STATES, depends=DEPENDS),
        'get_raw_products')

    @classmethod
    def __setup__(cls):
        super(Template, cls).__setup__()
        if cls.products.states.get('invisible'):
            cls.products.states['invisible'] = Or(
                cls.products.states['invisible'],
                Eval('has_raw_products', False))
        else:
            cls.products.states['invisible'] = Eval('has_raw_products', False)

    @staticmethod
    def default_has_raw_products():
        return False

    def get_main_products(self, name):
        if not self.has_raw_products:
            return []
        return [p.id for p in self.products if not p.is_raw_product]

    @classmethod
    def set_main_products(cls, templates, name, value):
        if not value:
            return
        cls.write(templates, {
                'products': value,
                })

    def get_raw_products(self, name):
        if not self.has_raw_products:
            return []
        return [p.id for p in self.products if p.is_raw_product]

    @fields.depends('has_raw_products', 'products')
    def on_change_has_raw_products(self):
        Product = Pool().get('product.product')
        if self.has_raw_products:
            self.products = []
        elif not self.products:
            self.products = Product.default_get(Product._fields.keys())

    @classmethod
    def validate(cls, templates):
        super(Template, cls).validate(templates)
        for template in templates:
            for product in template.products:
                product.check_raw_product()

    def update_variant_product(self, products, variant):
        """
        Compatibility with product_variant module (extras_depend)
        """
        Config = Pool().get('product.configuration')
        config = Config(1)

        def _super_call_with_prefix(products_sublist, prefix):
            if not products_sublist or not prefix:
                return
            with Transaction().set_context(product_raw_variant_prefix=prefix):
                super(Template, self).update_variant_product(products_sublist,
                    variant)
                for product in products_sublist:
                    products.remove(product)

        if self.has_raw_products:
            if config.main_product_prefix:
                main_products = tuple(p for p in products
                    if not p.is_raw_product)
                _super_call_with_prefix(main_products,
                    config.main_product_prefix)
            if config.raw_product_prefix:
                raw_products = tuple(p for p in products if p.is_raw_product)
                _super_call_with_prefix(raw_products,
                    config.raw_product_prefix)

        if products:
            super(Template, self).update_variant_product(products,
                variant)


    @classmethod
    def create_variant_code(cls, basecode, variant):
        """
        Compatibility with product_variant module (extras_depend)
        """
        code = super(Template, cls).create_variant_code(basecode, variant)

        prefix = Transaction().context.get('product_raw_variant_prefix')
        if prefix:
            code = prefix + code
        return code

    @classmethod
    def create(cls, vlist):
        new_templates = super(Template, cls).create(vlist)
        for template in new_templates:
            if not template.has_raw_products:
                continue
            template.create_missing_raw_products()
        return new_templates

    @classmethod
    def delete(cls, templates):
        pool = Pool()
        Product = pool.get('product.product')
        to_delete = []
        for template in templates:
            if template.has_raw_products:
                to_delete.extend(list(template.main_products))
        if to_delete:
            Product.delete(to_delete)
        super(Template, cls).delete(templates)

    @classmethod
    def copy(cls, templates, defaults=None):
        if defaults is None:
            defaults = {}
        defaults = defaults.copy()
        raw_templates = [t for t in templates if t.has_raw_products]
        not_raw_templates = [t for t in templates if not t.has_raw_products]
        raw_defaults = defaults.copy()
        raw_defaults.setdefault('products', [])
        new_raw = (super(Template, cls).copy(raw_templates, raw_defaults)
            if raw_templates else [])
        new_main = (super(Template, cls).copy(not_raw_templates, defaults)
            if not_raw_templates else [])
        return new_raw + new_main

    def create_missing_raw_products(self):
        Product = Pool().get('product.product')

        logging.getLogger(self.__name__).info("create_missing_raw_products()")
        products_missing_raw_variant = [p for p in self.products
            if not p.raw_product and not p.is_raw_product]
        if not products_missing_raw_variant:
            return {}

        with Transaction().set_context(no_create_raw_products=True):
            logging.getLogger(self.__name__).info("copying %d products"
                % len(products_missing_raw_variant))
            missing_raw_products = Product.copy(products_missing_raw_variant,
                default={
                    'has_raw_products': True,
                    'is_raw_product': True,
                    })
            for raw_product, product in izip(missing_raw_products,
                    products_missing_raw_variant):
                product.raw_product = raw_product
                product.save()
        logging.getLogger(self.__name__).info(
            "create_missing_raw_products() finished")
        return missing_raw_products


class Product:
    __name__ = 'product.product'

    has_raw_products = fields.Function(fields.Boolean('Has Raw Variants'),
        'on_change_with_has_raw_products', searcher='search_has_raw_products')
    is_raw_product = fields.Boolean('Is Raw Variant', readonly=True,
        states={
            'invisible': And(~Eval('_parent_template',
                    {}).get('has_raw_products', False),
                ~Eval('has_raw_products', False)),
            }, depends=['has_raw_products'])
    raw_product = fields.One2One('product.product-product.raw_product',
        'product', 'raw_product', 'Raw Variant', readonly=True,
        domain=[
            ('template', '=', Eval('template')),
            ('has_raw_products', '=', True),
            ('is_raw_product', '=', True),
            ('id', '!=', Eval('id', 0)),
            ],
        states={
            'invisible': Or(
                And(~Eval('_parent_template', {}).get('has_raw_products',
                        False),
                    ~Eval('has_raw_products', False)),
                Eval('is_raw_product', False)),
            },
        depends=['template', 'id', 'has_raw_products', 'is_raw_product'])
    main_product = fields.One2One('product.product-product.raw_product',
        'raw_product', 'product', 'Main Variant', readonly=True, states={
            'invisible': Or(
                And(~Eval('_parent_template', {}).get('has_raw_products',
                        False),
                    ~Eval('has_raw_products', False)),
                ~Bool(Eval('is_raw_product'))),
            }, depends=['has_raw_products', 'is_raw_product'])

    @classmethod
    def __setup__(cls):
        super(Product, cls).__setup__()
        cls._error_messages.update({
                'unexpected_raw_or_main_product':
                    'The Variant "%s" has a Raw or Main Variant but its '
                    'template doesn\'t have the mark "Has Raw Variants".',
                'unexpected_raw_product':
                    'The Variant "%s" has a Raw Variant but it is configured '
                    'as "Is Raw Variant", which doesn\'t make sense.',
                'unexpected_main_product':
                    'The Variant "%s" has a Main Variant but it isn\'t '
                    'configured as "Is Raw Variant", which doesn\'t make '
                    'sense.',
                'delete_raw_products_forbidden':
                    'Delete raw variants is forbidden.\n'
                    'You are trying to delete the variant "%(raw_product)s" '
                    'but it is defined as Raw Variant for product '
                    '"%(product)s".',
                })

    @fields.depends('template')
    def on_change_with_has_raw_products(self, name=None):
        return self.template and self.template.has_raw_products or False

    @classmethod
    def search_has_raw_products(cls, name, clause):
        return [('template.has_raw_products', ) + tuple(clause[1:])]

    @classmethod
    def validate(cls, products):
        super(Product, cls).validate(products)
        for product in products:
            product.check_raw_product()

    def check_raw_product(self):
        if (not self.has_raw_products and
                (self.raw_product or self.main_product)):
            self.raise_user_error('unexpected_raw_or_main_product',
                (self.rec_name,))
        if not self.has_raw_products:
            return
        if self.is_raw_product and self.raw_product:
            self.raise_user_error('unexpected_raw_product', (self.rec_name,))
        if not self.is_raw_product and self.main_product:
            self.raise_user_error('unexpected_main_product', (self.rec_name,))

    @classmethod
    def create(cls, vlist):
        pool = Pool()
        Template = pool.get('product.template')
        Config = pool.get('product.configuration')
        config = Config.get_singleton()

        create_raw_products = not Transaction().context.get(
            'no_create_raw_products', False)
        for vals in vlist:
            if vals.get('has_raw_products') or (vals.get('template') and
                    Template(vals['template']).has_raw_products):
                code = vals.get('code')
                if code is None:
                    code = ''
                if (vals.get('raw_product', False) or (
                            not vals.get('main_product') and
                            not vals.get('is_raw_product'))):
                    vals['is_raw_product'] = False
                    if config and config.main_product_prefix:
                        vals['code'] = config.main_product_prefix + code
                if (config and vals.get('is_raw_product', False) and
                        config.raw_product_prefix):
                    vals['code'] = config.raw_product_prefix + code

        new_products = super(Product, cls).create(vlist)
        if not create_raw_products:
            return new_products

        products_missing_raw_product = [p for p in new_products
            if (p.has_raw_products and not p.is_raw_product and
                not p.raw_product)]
        for product in products_missing_raw_product:
            product.create_raw_product()
        return new_products

    def create_raw_product(self):
        pool = Pool()
        Config = pool.get('product.configuration')
        config = Config.get_singleton()

        logging.getLogger(self.__name__).info("create_raw_product(%s)" % self)
        with Transaction().set_context(no_create_raw_products=True):
            code = self.code
            if config and config.main_product_prefix and code:
                code = code.replace(config.main_product_prefix, '')
            raw_product, = self.copy([self], default={
                    'code': code,
                    'is_raw_product': True,
                    'main_product': self.id,
                    })
        return raw_product

    @classmethod
    def delete(cls, products):
        to_delete = []
        for product in products:
            if product.has_raw_products:
                if product.raw_product:
                    to_delete.append(product.raw_product)
                elif product.main_product:
                    cls.raise_user_error('delete_raw_products_forbidden', {
                            'raw_product': product.rec_name,
                            'product': product.main_product,
                            })
            to_delete.append(product)
        super(Product, cls).delete(to_delete)


class ProductRawProduct(ModelSQL):
    'Main Variant - Raw Variant'
    __name__ = 'product.product-product.raw_product'
    product = fields.Many2One('product.product', 'Main Variant',
        ondelete='CASCADE', required=True, select=True)
    raw_product = fields.Many2One('product.product', 'Raw Variant',
        ondelete='CASCADE', required=True, select=True)

    @classmethod
    def __setup__(cls):
        super(ProductRawProduct, cls).__setup__()
        t = cls.__table__()
        cls._sql_constraints += [
            ('product_unique', Unique(t, t.product),
                'The Main Variant must be unique.'),
            ('raw_product_unique', Unique(t, t.raw_product),
                'The Raw Variant must be unique.'),
            ]
