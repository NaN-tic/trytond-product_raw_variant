# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from . import product


def register():
    Pool.register(
        product.Configuration,
        product.Template,
        product.Product,
        product.ProductRawProduct,
        module='product_raw_variant', type_='model')
