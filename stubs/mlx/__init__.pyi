from collections.abc import Callable
from typing import Any

class Mlx:
    def mlx_init(self) -> Any: ...
    def mlx_new_window(
        self, mlx_ptr: Any, width: int, height: int, title: str
    ) -> Any: ...
    def mlx_destroy_window(self, mlx_ptr: Any, win_ptr: Any) -> int: ...
    def mlx_new_image(
        self, mlx_ptr: Any, width: int, height: int
    ) -> Any: ...
    def mlx_get_data_addr(
        self, img_ptr: Any
    ) -> tuple[Any, int, int, int]: ...
    def mlx_put_image_to_window(
        self, mlx_ptr: Any, win_ptr: Any, img_ptr: Any, x: int, y: int
    ) -> int: ...
    def mlx_destroy_image(self, mlx_ptr: Any, img_ptr: Any) -> int: ...
    def mlx_string_put(
        self,
        mlx_ptr: Any,
        win_ptr: Any,
        x: int,
        y: int,
        color: int,
        string: str,
    ) -> int: ...
    def mlx_key_hook(
        self,
        win_ptr: Any,
        callback: Callable[[int, Any], int],
        param: Any,
    ) -> int: ...
    def mlx_hook(
        self,
        win_ptr: Any,
        x_event: int,
        x_mask: int,
        callback: Callable[..., int],
        param: Any,
    ) -> int: ...
    def mlx_expose_hook(
        self,
        win_ptr: Any,
        callback: Callable[[Any], None],
        param: Any,
    ) -> int: ...
    def mlx_loop_hook(
        self, mlx_ptr: Any, callback: Callable[[Any], int], param: Any
    ) -> int: ...
    def mlx_do_sync(self, mlx_ptr: Any) -> int: ...
    def mlx_loop(self, mlx_ptr: Any) -> int: ...
    def mlx_loop_exit(self, mlx_ptr: Any) -> int: ...