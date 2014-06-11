# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
import logging

from trytond.model import ModelSQL, fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import And, Bool, Eval, Or
from trytond.transaction import Transaction

__all__ = ['Template', 'Product', 'ProductRawProduct']
__metaclass__ = PoolMeta

STATES = {
    'readonly': ~Eval('active', True),
    'invisible': ~Eval('has_raw_products', False),
    }
DEPENDS = ['active', 'has_raw_products', 'products']


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

    @classmethod
    def validate(cls, templates):
        super(Template, cls).validate(templates)
        for template in templates:
            for product in template.products:
                product.check_raw_product()

    @classmethod
    def create(cls, vlist):
        new_templates = super(Template, cls).create(vlist)
        for template in new_templates:
            if not template.has_raw_products:
                continue
            template.create_missing_raw_products()
        return new_templates

    @classmethod
    def write(cls, templates, vals):
        products_to_create_main_variant = []
        if vals.get('has_raw_products', False):
            for template in templates:
                products_to_create_main_variant = (
                    template.prepare_raw_products_vals())
        super(Template, cls).write(templates, vals)
        if products_to_create_main_variant:
            for product in products_to_create_main_variant:
                product.create_main_product()

    def prepare_raw_products_vals(self):
        Product = Pool().get('product.product')

        products_missing_raw_variant = [p for p in self.products
            if not p.raw_product and not p.is_raw_product]
        if not products_missing_raw_variant:
            return None

        Product.write(products_missing_raw_variant, {
                    'is_raw_product': True,
                    })
        return products_missing_raw_variant

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
            for i, product in enumerate(products_missing_raw_variant):
                product.raw_product = missing_raw_products[i]
                product.save()
        logging.getLogger(self.__name__).info(
            "create_missing_raw_products() finished")
        return missing_raw_products


class Product:
    __name__ = 'product.product'

    has_raw_products = fields.Function(fields.Boolean('Has Raw Variants'),
        'on_change_with_has_raw_products', searcher='search_has_raw_products')
    is_raw_product = fields.Boolean('Is Raw Variant', states={
            'invisible': And(~Eval('_parent_template',
                    {}).get('has_raw_products', False),
                ~Eval('has_raw_products', False)),
            'readonly': Bool(Eval('main_product', 0)),
            }, depends=['has_raw_products'])
    raw_product = fields.One2One('product.product-product.raw_product',
        'product', 'raw_product', 'Raw Variant', domain=[
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
                    'Delete raw products is forbidden.\n'
                    'You are trying to delete product "%(raw_product)s" but '
                    'it is defined as Raw Variant for product "%(product)s".',
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

        create_raw_products = not Transaction().context.get(
            'no_create_raw_products', False)
        if create_raw_products:
            for vals in vlist:
                if vals.get('has_raw_products') or (vals.get('template') and
                        Template(vals['template']).has_raw_products):
                    if not vals.get('raw_product'):
                        vals['is_raw_product'] = True

        new_products = super(Product, cls).create(vlist)
        if not create_raw_products:
            return new_products

        products_missing_main_product = [p for p in new_products
            if (p.has_raw_products and p.is_raw_product and
                not p.main_product)]
        if not products_missing_main_product:
            return new_products
        for product in products_missing_main_product:
            product.create_main_product()
        return new_products

    def create_main_product(self):
        logging.getLogger(self.__name__).info("create_main_product(%s)" % self)
        with Transaction().set_context(no_create_raw_products=True):
            main_product, = self.copy([self], default={
                    'is_raw_product': False,
                    'raw_product': self.id,
                    })
        return main_product

    @classmethod
    def delete(cls, products):
        for product in products:
            if product.has_raw_products and product.main_product:
                cls.raise_user_error('delete_raw_products_forbidden', {
                        'raw_product': product.rec_name,
                        'product': product.main_product,
                        })
        super(Product, cls).delete(products)


class ProductRawProduct(ModelSQL):
    'Product - Raw Product'
    __name__ = 'product.product-product.raw_product'
    product = fields.Many2One('product.product', 'Product', ondelete='CASCADE',
        required=True, select=True)
    raw_product = fields.Many2One('product.product', 'Raw Product',
        ondelete='CASCADE', required=True, select=True)

    @classmethod
    def __setup__(cls):
        super(ProductRawProduct, cls).__setup__()
        cls._sql_constraints += [
            ('product_unique', 'UNIQUE(product)',
                'The Product must be unique.'),
            ('raw_product_unique', 'UNIQUE(raw_product)',
                'The RawProduct must be unique.'),
            ]
