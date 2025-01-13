import unittest
import os
import pygame
import pygame.camera


class CameraModuleTest(unittest.TestCase):
    def setUp(self):
        pygame.init()

        pygame.camera.init()

    @unittest.skipIf(
        os.environ.get("SDL_VIDEODRIVER") in ["dummy", "android"],
        "requires the SDL_VIDEODRIVER to be non dummy",
    )
    def test_camera(self):
        cameras = pygame.camera.list_cameras()

        if len(cameras) == 0:
            self.skipTest("No cameras found")

        cam = pygame.camera.Camera(cameras[0], (640, 480))
        cam.start()
        image = cam.get_image()
        self.assertIsNotNone(image, "Could not capture image")
        cam.stop()

    def tearDown(self):
        pygame.camera.quit()
        pygame.quit()


if __name__ == "__main__":
    unittest.main()
