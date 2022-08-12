
import unittest
from .list import find_item, find_index


class ListTest(unittest.TestCase):
  def test_find(self):
    l = [1, 2, 3]
    found = find_item(l, lambda item: item == 2)
    self.assertEqual(found, 2)

    not_found = find_item(l, lambda item: item == 7)
    self.assertIsNone(not_found)

  def test_find_index(self):
    l = [1, 2, 3]
    found_index = find_index(l, lambda item: item == 2)
    self.assertEqual(found_index, 1)

    not_found_index = find_index(l, lambda item: item == 10)
    self.assertEqual(not_found_index, - 1)




  

