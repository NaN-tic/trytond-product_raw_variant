#!/usr/bin/env python
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from decimal import Decimal
import unittest
import trytond.tests.test_tryton
from trytond.tests.test_tryton import test_view, test_depends
from trytond.tests.test_tryton import POOL, DB_NAME, USER, CONTEXT
from trytond.transaction import Transaction


class TestCase(unittest.TestCase):
    'Test module'

    def setUp(self):
        trytond.tests.test_tryton.install_module('product_raw_variant')
        self.configuration = POOL.get('product.configuration')
        self.template = POOL.get('product.template')
        self.product = POOL.get('product.product')
        self.uom = POOL.get('product.uom')

    def test0005views(self):
        'Test views'
        test_view('product_raw_variant')

    def test0006depends(self):
        'Test depends'
        test_depends()

    def test0010_raw_variant_creation(self):
        with Transaction().start(DB_NAME, USER, context=CONTEXT):
            config = self.configuration(1)
            config.raw_product_prefix = 'RAW'
            config.main_product_prefix = 'MAIN'
            config.save()
            unit, = self.uom.search([('name', '=', 'Unit')])

            template, = self.template.create([{
                        'name': 'Test Product Raw',
                        'type': 'goods',
                        'list_price': Decimal(1),
                        'cost_price': Decimal(0),
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
            self.product.create([{
                        'template': template.id,
                        'code': '11',
                        }])
            template = self.template(template.id)
            raw_product, new_raw_product = template.raw_products
            self.assertEqual(raw_product.code, 'RAW10')
            self.assertEqual(new_raw_product.code, 'RAW11')
            main_product, new_main_product = template.main_products
            self.assertEqual(main_product.code, 'MAIN10')
            self.assertEqual(new_main_product.code, 'MAIN11')
            self.product.delete([new_main_product])
            template = self.template(template.id)
            self.assertEqual(len(template.raw_products), 1)


def suite():
    suite = trytond.tests.test_tryton.suite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestCase))
    return suite
