#!/usr/bin/env python
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from decimal import Decimal
import unittest
import trytond.tests.test_tryton
from trytond.tests.test_tryton import ModuleTestCase, with_transaction
from trytond.pool import Pool


class TestCase(ModuleTestCase):
    'Test module'
    module = 'product_raw_variant'

    @with_transaction()
    def test0010_raw_variant_creation(self):
        pool = Pool()
        Configuration = pool.get('product.configuration')
        Template = pool.get('product.template')
        Product = pool.get('product.product')
        Uom = pool.get('product.uom')

        config = Configuration(1)
        config.raw_product_prefix = 'RAW'
        config.main_product_prefix = 'MAIN'
        config.save()
        unit, = Uom.search([('name', '=', 'Unit')])

        template, = Template.create([{
                    'name': 'Test Product Raw',
                    'type': 'goods',
                    'list_price': Decimal(1),
                    'cost_price_method': 'fixed',
                    'default_uom': unit.id,
                    'has_raw_products': True,
                     'main_products': [('create', [{
                                    'code': '10',
                                    }])],
                    }])
        raw_product, = template.raw_products
        self.assertEqual(raw_product.code, 'RAW10')
        main_product, = template.main_products
        self.assertEqual(main_product.code, 'MAIN10')
        Product.create([{
                    'template': template.id,
                    'code': '11',
                    }])
        template = Template(template.id)
        raw_product, new_raw_product = template.raw_products
        self.assertEqual(raw_product.code, 'RAW10')
        self.assertEqual(new_raw_product.code, 'RAW11')
        main_product, new_main_product = template.main_products
        self.assertEqual(main_product.code, 'MAIN10')
        self.assertEqual(new_main_product.code, 'MAIN11')
        Product.delete([new_main_product])
        template = Template(template.id)
        self.assertEqual(len(template.raw_products), 1)


def suite():
    suite = trytond.tests.test_tryton.suite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestCase))
    return suite
