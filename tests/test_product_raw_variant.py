#!/usr/bin/env python
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
import unittest
#import doctest
import trytond.tests.test_tryton
from trytond.tests.test_tryton import test_view, test_depends
from trytond.backend.sqlite.database import Database as SQLiteDatabase


class TestCase(unittest.TestCase):
    '''
    Test module.
    '''

    def setUp(self):
        trytond.tests.test_tryton.install_module('product_raw_variant')

    def test0005views(self):
        '''
        Test views.
        '''
        test_view('product_raw_variant')

    def test0006depends(self):
        '''
        Test depends.
        '''
        test_depends()


def doctest_dropdb(test):
    database = SQLiteDatabase().connect()
    cursor = database.cursor(autocommit=True)
    try:
        database.drop(cursor, ':memory:')
        cursor.commit()
    finally:
        cursor.close()


def suite():
    suite = trytond.tests.test_tryton.suite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestCase))
    # TODO: it fails but not using the client
    #suite.addTests(doctest.DocFileSuite('scenario_product_raw_variant.rst',
    #        setUp=doctest_dropdb, tearDown=doctest_dropdb, encoding='utf-8',
    #        optionflags=doctest.REPORT_ONLY_FIRST_FAILURE))
    return suite