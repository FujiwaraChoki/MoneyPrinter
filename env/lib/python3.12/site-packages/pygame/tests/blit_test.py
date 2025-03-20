import unittest

import pygame
from pygame.locals import *

from time import time


class BlitTest(unittest.TestCase):
    def test_SRCALPHA(self):
        """SRCALPHA tests."""
        # blend(s, 0, d) = d
        s = pygame.Surface((1, 1), SRCALPHA, 32)
        s.fill((255, 255, 255, 0))

        d = pygame.Surface((1, 1), SRCALPHA, 32)
        d.fill((0, 0, 255, 255))

        s.blit(d, (0, 0))
        self.assertEqual(s.get_at((0, 0)), d.get_at((0, 0)))

        # blend(s, 255, d) = s
        s = pygame.Surface((1, 1), SRCALPHA, 32)
        s.fill((123, 0, 0, 255))
        s1 = pygame.Surface((1, 1), SRCALPHA, 32)
        s1.fill((123, 0, 0, 255))
        d = pygame.Surface((1, 1), SRCALPHA, 32)
        d.fill((10, 0, 0, 0))
        s.blit(d, (0, 0))
        self.assertEqual(s.get_at((0, 0)), s1.get_at((0, 0)))

        # TODO: these should be true too.
        # blend(0, sA, 0) = 0
        # blend(255, sA, 255) = 255
        # blend(s, sA, d) <= 255

    def test_BLEND(self):
        """BLEND_ tests."""

        # test that it doesn't overflow, and that it is saturated.
        s = pygame.Surface((1, 1), SRCALPHA, 32)
        s.fill((255, 255, 255, 0))

        d = pygame.Surface((1, 1), SRCALPHA, 32)
        d.fill((0, 0, 255, 255))

        s.blit(d, (0, 0), None, BLEND_ADD)

        # print("d %s" % (d.get_at((0,0)),))
        # print(s.get_at((0,0)))
        # self.assertEqual(s.get_at((0,0))[2], 255 )
        # self.assertEqual(s.get_at((0,0))[3], 0 )

        s.blit(d, (0, 0), None, BLEND_RGBA_ADD)
        # print(s.get_at((0,0)))
        self.assertEqual(s.get_at((0, 0))[3], 255)

        # test adding works.
        s.fill((20, 255, 255, 0))
        d.fill((10, 0, 255, 255))
        s.blit(d, (0, 0), None, BLEND_ADD)
        self.assertEqual(s.get_at((0, 0))[2], 255)

        # test subbing works.
        s.fill((20, 255, 255, 0))
        d.fill((10, 0, 255, 255))
        s.blit(d, (0, 0), None, BLEND_SUB)
        self.assertEqual(s.get_at((0, 0))[0], 10)

        # no overflow in sub blend.
        s.fill((20, 255, 255, 0))
        d.fill((30, 0, 255, 255))
        s.blit(d, (0, 0), None, BLEND_SUB)
        self.assertEqual(s.get_at((0, 0))[0], 0)


class BlitsTest(unittest.TestCase):
    """Tests for pygame.Surface.blits"""

    def setUp(self):
        self.NUM_SURFS = 255
        self.PRINT_TIMING = 0
        self.dst = pygame.Surface((self.NUM_SURFS * 10, 10), SRCALPHA, 32)
        self.dst.fill((230, 230, 230))
        self.blit_list = self.make_blit_list(self.NUM_SURFS)

    def make_blit_list(self, num_surfs):
        """Generate a list of tuples representing surfaces and destinations
        for blitting"""

        blit_list = []
        for i in range(num_surfs):
            dest = (i * 10, 0)
            surf = pygame.Surface((10, 10), SRCALPHA, 32)
            color = (i * 1, i * 1, i * 1)
            surf.fill(color)
            blit_list.append((surf, dest))
        return blit_list

    def custom_blits(self, blit_list):
        """Custom blits method that manually iterates over the blit_list and blits
        each surface onto the destination."""

        for surface, dest in blit_list:
            self.dst.blit(surface, dest)

    def test_custom_blits_performance(self):
        """Checks time performance of the custom blits method"""

        t0 = time()
        results = self.custom_blits(self.blit_list)
        t1 = time()
        if self.PRINT_TIMING:
            print(f"python blits: {t1 - t0}")

    def test_blits_performance(self):
        """Checks time performance of blits"""

        t0 = time()
        results = self.dst.blits(self.blit_list)
        t1 = time()
        if self.PRINT_TIMING:
            print(f"Surface.blits: {t1 - t0}")

        # Measure time performance of blits with doreturn=0
        t0 = time()
        results = self.dst.blits(self.blit_list, doreturn=0)
        t1 = time()
        if self.PRINT_TIMING:
            print(f"Surface.blits doreturn=0: {t1 - t0}")

        # Measure time performance of blits using a generator
        t0 = time()
        results = self.dst.blits(((surf, dest) for surf, dest in self.blit_list))
        t1 = time()
        if self.PRINT_TIMING:
            print(f"Surface.blits generator: {t1 - t0}")

    def test_blits_correctness(self):
        """Checks the correctness of the colors on the destination
        after blitting and tests that the length of the results list
        matches the number of surfaces blitted."""

        results = self.dst.blits(self.blit_list)
        for i in range(self.NUM_SURFS):
            color = (i * 1, i * 1, i * 1)
            self.assertEqual(self.dst.get_at((i * 10, 0)), color)
            self.assertEqual(self.dst.get_at(((i * 10) + 5, 5)), color)

        self.assertEqual(len(results), self.NUM_SURFS)

    def test_blits_doreturn(self):
        """Tests that when doreturn=0, it returns None"""

        results = self.dst.blits(self.blit_list, doreturn=0)
        self.assertEqual(results, None)

    def test_blits_not_sequence(self):
        """Tests that calling blits with an invalid non-sequence None argument
        raises a ValueError."""

        dst = pygame.Surface((100, 10), SRCALPHA, 32)
        with self.assertRaises(ValueError):
            dst.blits(None)

    def test_blits_wrong_length(self):
        """Tests that calling blits with an invalid sequence containing a single surface
        (without a destination) raises a ValueError."""

        dst = pygame.Surface((100, 10), SRCALPHA, 32)
        with self.assertRaises(ValueError):
            dst.blits([pygame.Surface((10, 10), SRCALPHA, 32)])

    def test_blits_bad_surf_args(self):
        """Tests that calling blits with a sequence containing an invalid tuple of
        None arguments raises a TypeError."""

        dst = pygame.Surface((100, 10), SRCALPHA, 32)
        with self.assertRaises(TypeError):
            dst.blits([(None, None)])

    def test_blits_bad_dest(self):
        """Tests that calling blits with a sequence containing an invalid tuple with a
        destination of None raises a TypeError."""

        dst = pygame.Surface((100, 10), SRCALPHA, 32)
        with self.assertRaises(TypeError):
            dst.blits([(pygame.Surface((10, 10), SRCALPHA, 32), None)])


if __name__ == "__main__":
    unittest.main()
