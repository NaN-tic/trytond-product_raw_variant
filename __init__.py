# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from .product import *


def register():
    Pool.register(
        Configuration,
        Template,
        Product,
        ProductRawProduct,
        module='product_raw_variant', type_='model')
