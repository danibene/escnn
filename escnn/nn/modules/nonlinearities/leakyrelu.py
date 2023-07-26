from typing import Any, List, Tuple

import numpy as np
import torch
import torch.nn.functional as F
from escnn.gspaces import GSpace
from escnn.nn import FieldType, GeometricTensor

from ..equivariant_module import EquivariantModule

__all__ = ["LeakyReLU"]


class LeakyReLU(EquivariantModule):
    def __init__(
        self, in_type: FieldType, negative_slope: float = 0.01, inplace: bool = False
    ):
        r"""

        Module that implements a pointwise LeakyReLU to every channel independently.
        The input representation is preserved by this operation and, therefore, it equals the output
        representation.

        Only representations supporting pointwise non-linearities are accepted as input field type.

        Args:
            in_type (FieldType):  the input field type
            negative_slope (float, optional): Controls the angle of the negative slope (which is used for negative input values). Default: 0.01
            inplace (bool, optional): can optionally do the operation in-place. Default: ``False``

        """

        assert isinstance(in_type.gspace, GSpace)

        super(LeakyReLU, self).__init__()

        for r in in_type.representations:
            assert (
                "pointwise" in r.supported_nonlinearities
            ), 'Error! Representation "{}" does not support "pointwise" non-linearity'.format(
                r.name
            )

        self.space = in_type.gspace
        self.in_type = in_type

        # the representation in input is preserved
        self.out_type = in_type

        self._negative_slope = negative_slope
        self._inplace = inplace

    def forward(self, input: GeometricTensor) -> GeometricTensor:
        r"""

        Applies leaky-ReLU function on the input fields

        Args:
            input (GeometricTensor): the input feature map

        Returns:
            the resulting feature map after relu has been applied

        """

        assert (
            input.type == self.in_type
        ), "Error! the type of the input does not match the input type of this module"
        return GeometricTensor(
            F.leaky_relu(
                input.tensor, negative_slope=self._negative_slope, inplace=self._inplace
            ),
            self.out_type,
            input.coords,
        )

    def evaluate_output_shape(self, input_shape: Tuple[int, ...]) -> Tuple[int, ...]:
        assert len(input_shape) >= 2
        assert input_shape[1] == self.in_type.size

        b, c = input_shape[:2]
        spatial_shape = input_shape[2:]

        return (b, self.out_type.size, *spatial_shape)

    def check_equivariance(
        self, atol: float = 1e-6, rtol: float = 1e-5
    ) -> List[Tuple[Any, float]]:
        c = self.in_type.size

        x = torch.randn(3, c, 10, 10)

        x = GeometricTensor(x, self.in_type)

        errors = []

        for el in self.space.testing_elements:
            out1 = self(x).transform_fibers(el)
            out2 = self(x.transform_fibers(el))

            errs = (out1.tensor - out2.tensor).detach().numpy()
            errs = np.abs(errs).reshape(-1)
            print(el, errs.max(), errs.mean(), errs.var())

            assert torch.allclose(
                out1.tensor, out2.tensor, atol=atol, rtol=rtol
            ), 'The error found during equivariance check with element "{}" is too high: max = {}, mean = {} var ={}'.format(
                el, errs.max(), errs.mean(), errs.var()
            )

            errors.append((el, errs.mean()))

        return errors

    def extra_repr(self):
        return "inplace={}, type={}".format(self._inplace, self.in_type)

    def export(self):
        r"""
        Export this module to a normal PyTorch :class:`torch.nn.LeakyReLU` module and set to "eval" mode.

        """

        self.eval()

        return torch.nn.LeakyReLU(
            negative_slope=self._negative_slope, inplace=self._inplace
        )
