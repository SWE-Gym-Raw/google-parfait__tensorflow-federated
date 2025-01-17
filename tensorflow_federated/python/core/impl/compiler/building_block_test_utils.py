# Copyright 2018, The TensorFlow Federated Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Utilities for testing building blocks."""

from typing import Union

import federated_language
import numpy as np

from google.protobuf import any_pb2


def create_any_proto_from_array(value: np.ndarray):
  """Creates an `Any` proto for the given `np.array` value."""
  test_proto = federated_language.array_to_proto(value)
  any_proto = any_pb2.Any()
  any_proto.Pack(test_proto)
  return any_proto


def create_chained_calls(functions, arg):
  r"""Creates a chain of `n` calls.

       Call
      /    \
  Comp      ...
               \
                Call
               /    \
           Comp      Comp

  The first functional computation in `functions` must have a parameter type
  that is assignable from the type of `arg`, each other functional computation
  in `functions` must have a parameter type that is assignable from the previous
  functional computations result type.

  Args:
    functions: A Python list of functional computations.
    arg: A `federated_language.framework.ComputationBuildingBlock`.

  Returns:
    A `federated_language.framework.Call`.
  """
  for fn in functions:
    if not fn.parameter_type.is_assignable_from(arg.type_signature):
      raise TypeError(
          'The parameter of the function is of type {}, and the argument is of '
          'an incompatible type {}.'.format(
              str(fn.parameter_type), str(arg.type_signature)
          )
      )
    call = federated_language.framework.Call(fn, arg)
    arg = call
  return call


def create_whimsy_block(
    comp, variable_name, variable_type: type[np.generic] = np.int32
):
  r"""Returns an identity block.

           Block
          /     \
     [x=1]       Comp

  Args:
    comp: The computation to use as the result.
    variable_name: The name of the variable.
    variable_type: The type of the variable.
  """
  ref = federated_language.framework.Literal(
      1, federated_language.TensorType(variable_type)
  )
  return federated_language.framework.Block([(variable_name, ref)], comp)


def create_whimsy_called_intrinsic(parameter_name, parameter_type=np.int32):
  r"""Returns a whimsy called intrinsic.

            Call
           /    \
  intrinsic      Ref(x)

  Args:
    parameter_name: The name of the parameter.
    parameter_type: The type of the parameter.
  """
  intrinsic_type = federated_language.FunctionType(
      parameter_type, parameter_type
  )
  intrinsic = federated_language.framework.Intrinsic(
      'intrinsic', intrinsic_type
  )
  ref = federated_language.framework.Reference(parameter_name, parameter_type)
  return federated_language.framework.Call(intrinsic, ref)


def create_whimsy_called_federated_aggregate(
    accumulate_parameter_name='acc_param',
    merge_parameter_name='merge_param',
    report_parameter_name='report_param',
    value_type: type[np.generic] = np.int32,
):
  r"""Returns a whimsy called federated aggregate.

                      Call
                     /    \
  federated_aggregate      Tuple
                           |
                           [Lit(1), Lit(1), Lambda(x),   Lambda(x),   Lambda(x)]
                                            |            |            |
                                            Lit(1)       Lit(1)       Lit(1)

  Args:
    accumulate_parameter_name: The name of the accumulate parameter.
    merge_parameter_name: The name of the merge parameter.
    report_parameter_name: The name of the report parameter.
    value_type: The TFF type of the value to be aggregated, placed at CLIENTS.
  """
  tensor_type = federated_language.TensorType(value_type)
  value = federated_language.framework.create_federated_value(
      federated_language.framework.Literal(1, tensor_type),
      federated_language.CLIENTS,
  )
  literal_block = federated_language.framework.Literal(1, tensor_type)
  zero = literal_block
  accumulate_type = federated_language.StructType((value_type, value_type))
  accumulate_result = literal_block
  accumulate = federated_language.framework.Lambda(
      accumulate_parameter_name, accumulate_type, accumulate_result
  )
  merge_type = federated_language.StructType((value_type, value_type))
  merge_result = literal_block
  merge = federated_language.framework.Lambda(
      merge_parameter_name, merge_type, merge_result
  )
  report_result = literal_block
  report = federated_language.framework.Lambda(
      report_parameter_name, value_type, report_result
  )
  return federated_language.framework.create_federated_aggregate(
      value, zero, accumulate, merge, report
  )


def create_whimsy_called_federated_apply(
    parameter_name, parameter_type: type[np.generic] = np.int32
):
  r"""Returns a whimsy called federated apply.

                  Call
                 /    \
  federated_apply      Tuple
                       |
                       [Lambda(x), Lit(1)]
                        |
                        Ref(x)

  Args:
    parameter_name: The name of the parameter.
    parameter_type: The type of the parameter.
  """
  value = parameter_type(1)
  fn = create_identity_function(parameter_name, parameter_type)
  arg_type = federated_language.TensorType(parameter_type)
  arg = federated_language.framework.create_federated_value(
      federated_language.framework.Literal(value, arg_type),
      placement=federated_language.SERVER,
  )
  return federated_language.framework.create_federated_apply(fn, arg)


def create_whimsy_called_federated_broadcast(
    value_type: type[np.generic] = np.int32,
):
  r"""Returns a whimsy called federated broadcast.

                      Call
                     /    \
  federated_broadcast      Lit(1)

  Args:
    value_type: The type of the value.
  """
  value = value_type(1)
  tensor_type = federated_language.TensorType(value_type)
  value = federated_language.framework.create_federated_value(
      federated_language.framework.Literal(value, tensor_type),
      placement=federated_language.SERVER,
  )
  return federated_language.framework.create_federated_broadcast(value)


def create_whimsy_called_federated_map(
    parameter_name, parameter_type: type[np.generic] = np.int32
):
  r"""Returns a whimsy called federated map.

                Call
               /    \
  federated_map      Tuple
                     |
                     [Lambda(x), Lit(1)]
                      |
                      Ref(x)

  Args:
    parameter_name: The name of the parameter.
    parameter_type: The type of the parameter.
  """
  value = parameter_type(1)
  fn = create_identity_function(parameter_name, parameter_type)
  arg_type = federated_language.TensorType(parameter_type)
  arg = federated_language.framework.create_federated_value(
      federated_language.framework.Literal(value, arg_type),
      placement=federated_language.CLIENTS,
  )
  # TODO: b/338284242 - Replace this with a `Data` block once the compiler tests
  # do not use string equality.
  # pylint: disable=protected-access
  arg._type_signature = federated_language.FederatedType(
      arg_type, federated_language.CLIENTS, all_equal=False
  )
  # pylint: enable=protected-access
  return federated_language.framework.create_federated_map(fn, arg)


def create_whimsy_called_federated_map_all_equal(
    parameter_name, parameter_type: type[np.generic] = np.int32
):
  r"""Returns a whimsy called federated map.

                          Call
                         /    \
  federated_map_all_equal      Tuple
                               |
                               [Lambda(x), Lit(1)]
                                |
                                Ref(x)

  Args:
    parameter_name: The name of the parameter.
    parameter_type: The type of the parameter.
  """
  value = parameter_type(1)
  fn = create_identity_function(parameter_name, parameter_type)
  arg_type = federated_language.TensorType(parameter_type)
  arg = federated_language.framework.create_federated_value(
      federated_language.framework.Literal(value, arg_type),
      placement=federated_language.CLIENTS,
  )
  return federated_language.framework.create_federated_map_all_equal(fn, arg)


def create_whimsy_called_federated_mean(
    value_type: type[np.generic] = np.float32,
    weights_type: Union[type[np.generic], None] = None,
):
  """Returns a called federated mean."""
  value = value_type(1)
  value_type = federated_language.TensorType(value_type)
  values = federated_language.framework.create_federated_value(
      federated_language.framework.Literal(value, value_type),
      placement=federated_language.CLIENTS,
  )
  if weights_type is not None:
    weights_value = weights_type(1)
    weights_type = federated_language.TensorType(weights_type)
    weights = federated_language.framework.create_federated_value(
        federated_language.framework.Literal(weights_value, weights_type),
        placement=federated_language.CLIENTS,
    )
  else:
    weights = None
  return federated_language.framework.create_federated_mean(values, weights)


def create_whimsy_called_federated_secure_sum_bitwidth(
    value_type: type[np.generic] = np.int32,
):
  r"""Returns a whimsy called secure sum.

                       Call
                      /    \
  federated_secure_sum_bitwidth      [Lit(1), Lit(1)]

  Args:
    value_type: The type of the value.
  """
  lit_value = value_type(1)
  tensor_type = federated_language.TensorType(value_type)
  value = federated_language.framework.create_federated_value(
      federated_language.framework.Literal(lit_value, tensor_type),
      placement=federated_language.CLIENTS,
  )
  bitwidth = federated_language.framework.Literal(lit_value, tensor_type)
  return federated_language.framework.create_federated_secure_sum_bitwidth(
      value, bitwidth
  )


def create_whimsy_called_federated_sum(
    value_type: type[np.generic] = np.int32,
):
  r"""Returns a whimsy called federated sum.

                Call
               /    \
  federated_sum      Lit(a)

  Args:
    value_type: The type of the value.
  """
  value = value_type(1)
  tensor_type = federated_language.TensorType(value_type)
  value = federated_language.framework.create_federated_value(
      federated_language.framework.Literal(value, tensor_type),
      placement=federated_language.CLIENTS,
  )
  return federated_language.framework.create_federated_sum(value)


def create_whimsy_called_sequence_map(
    # TODO: b/338284242 - Remove any proto from function constructor once the
    # compiler tests no longer use string equality.
    parameter_name,
    parameter_type=np.int32,
    any_proto=any_pb2.Any(),
):
  r"""Returns a whimsy called sequence map.

               Call
              /    \
  sequence_map      Data(id)

  Args:
    parameter_name: The name of the parameter.
    parameter_type: The type of the parameter.
    any_proto: The any proto to use for the data block.
  """
  fn = create_identity_function(parameter_name, parameter_type)
  arg_type = federated_language.SequenceType(parameter_type)
  arg = federated_language.framework.Data(any_proto, arg_type)
  return federated_language.framework.create_sequence_map(fn, arg)


def create_whimsy_called_federated_value(
    placement: federated_language.framework.PlacementLiteral,
    value_type: type[np.generic] = np.int32,
):
  value = value_type(1)
  value = federated_language.framework.Literal(
      value, federated_language.TensorType(value_type)
  )
  return federated_language.framework.create_federated_value(value, placement)


def create_identity_block(variable_name, comp):
  r"""Returns an identity block.

           Block
          /     \
  [x=comp]       Ref(x)

  Args:
    variable_name: The name of the variable.
    comp: The computation to use as the variable.
  """
  ref = federated_language.framework.Reference(
      variable_name, comp.type_signature
  )
  return federated_language.framework.Block([(variable_name, comp)], ref)


def create_identity_block_with_whimsy_ref(
    variable_name, variable_type: type[np.generic] = np.int32
):
  r"""Returns an identity block with a whimsy `ref` computation.

             Block
            /     \
  [x=Lit(1)]       Ref(x)

  Args:
    variable_name: The name of the variable.
    variable_type: The type of the variable.
  """
  value = variable_type(1)
  literal = federated_language.framework.Literal(
      value, federated_language.TensorType(variable_type)
  )
  return create_identity_block(variable_name, literal)


def create_identity_function(parameter_name, parameter_type=np.int32):
  r"""Returns an identity function.

  Lambda(x)
  |
  Ref(x)

  Args:
    parameter_name: The name of the parameter.
    parameter_type: The type of the parameter.
  """
  ref = federated_language.framework.Reference(parameter_name, parameter_type)
  return federated_language.framework.Lambda(ref.name, ref.type_signature, ref)


def create_lambda_to_whimsy_called_intrinsic(
    parameter_name, parameter_type=np.int32
):
  r"""Returns a lambda to call a whimsy intrinsic.

            Lambda(x)
            |
            Call
           /    \
  intrinsic      Ref(x)

  Args:
    parameter_name: The name of the parameter.
    parameter_type: The type of the parameter.
  """
  call = create_whimsy_called_intrinsic(
      parameter_name=parameter_name, parameter_type=parameter_type
  )
  return federated_language.framework.Lambda(
      parameter_name, parameter_type, call
  )


def create_nested_syntax_tree():
  r"""Constructs computation with explicit ordering for testing traversals.

  The goal of this computation is to exercise each switch
  in transform_postorder_with_symbol_bindings, at least all those that recurse.

  The computation this function constructs can be represented as below.

  Notice that the body of the Lambda *does not depend on the Lambda's
  parameter*, so that if we were actually executing this call the argument will
  be thrown away.

  All leaf nodes are instances of `federated_language.framework.Lit`.

                            Call
                           /    \
                 Lambda('arg')   Lit(11)
                     |
                   Block('y','z')-------------
                  /                          |
  ['y'=Lit(1),'z'=Lit(2)]                    |
                                           Tuple
                                         /       \
                                   Block('v')     Block('x')-------
                                     / \              |            |
                       ['v'=Selection]  Lit(7)    ['x'=Lit(8)]     |
                             |                                     |
                             |                                     |
                             |                                 Block('w')
                             |                                   /   \
                           Tuple ------              ['w'=Lit(9)]     Lit(10)
                         /              \
                 Block('t')             Block('u')
                  /     \              /          \
        ['t'=L(3)]       Lit(4) ['u'=Lit(5)]       Lit(6)


  Postorder traversals:
  If we are reading Literal values, results of a postorder traversal should be:
  [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]

  If we are reading locals declarations, results of a postorder traversal should
  be:
  [t, u, v, w, x, y, z]

  And if we are reading both in an interleaved fashion, results of a postorder
  traversal should be:
  [1, 2, 3, 4, t, 5, 6, u, 7, v, 8, 9, 10, w, x, y, z, 11]

  Preorder traversals:
  If we are reading Literal values, results of a preorder traversal should be:
  [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]

  If we are reading locals declarations, results of a preorder traversal should
  be:
  [y, z, v, t, u, x, w]

  And if we are reading both in an interleaved fashion, results of a preorder
  traversal should be:
  [y, z, 1, 2, v, t, 3, 4, u, 5, 6, 7, x, 8, w, 9, 10, 11]

  Since we are also exposing the ability to hook into variable declarations,
  it is worthwhile considering the order in which variables are assigned in
  this tree. Notice that this order maps neither to preorder nor to postorder
  when purely considering the nodes of the tree above. This would be:
  [arg, y, z, t, u, v, x, w]

  Returns:
    An instance of `federated_language.framework.ComputationBuildingBlock`
    satisfying the description above.
  """
  tensor_type = federated_language.TensorType(np.int32)
  lit_c = federated_language.framework.Literal(3, tensor_type)
  lit_d = federated_language.framework.Literal(4, tensor_type)
  left_most_leaf = federated_language.framework.Block([('t', lit_c)], lit_d)

  lit_e = federated_language.framework.Literal(5, tensor_type)
  lit_f = federated_language.framework.Literal(6, tensor_type)
  center_leaf = federated_language.framework.Block([('u', lit_e)], lit_f)
  inner_tuple = federated_language.framework.Struct(
      [left_most_leaf, center_leaf]
  )

  selected = federated_language.framework.Selection(inner_tuple, index=0)
  lit_g = federated_language.framework.Literal(7, tensor_type)
  middle_block = federated_language.framework.Block([('v', selected)], lit_g)

  lit_i = federated_language.framework.Literal(8, tensor_type)
  lit_j = federated_language.framework.Literal(9, tensor_type)
  right_most_endpoint = federated_language.framework.Block(
      [('w', lit_i)], lit_j
  )

  lit_h = federated_language.framework.Literal(10, tensor_type)
  right_child = federated_language.framework.Block(
      [('x', lit_h)], right_most_endpoint
  )

  result = federated_language.framework.Struct([middle_block, right_child])
  lit_a = federated_language.framework.Literal(1, tensor_type)
  lit_b = federated_language.framework.Literal(2, tensor_type)
  whimsy_outer_block = federated_language.framework.Block(
      [('y', lit_a), ('z', lit_b)], result
  )
  whimsy_lambda = federated_language.framework.Lambda(
      'arg', tensor_type, whimsy_outer_block
  )
  whimsy_arg = federated_language.framework.Literal(11, tensor_type)
  called_lambda = federated_language.framework.Call(whimsy_lambda, whimsy_arg)

  return called_lambda
