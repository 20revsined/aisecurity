"""

"aisecurity.utils.graphs"

Graph/model utils.

"""

import tensorflow as tf
from tensorflow.contrib import tensorrt as trt
from tensorflow.python.framework import graph_io

from aisecurity.utils.preprocessing import timer

# GRAPH MANAGEMENT
@timer("Freezing time")
def freeze_graph(path_to_keras_model, save_dir=None, save_name="frozen_graph.pb"):

    tf.keras.backend.clear_session()

    def _freeze_graph(graph, session, output):
        with graph.as_default():
            variable = tf.graph_util.remove_training_nodes(graph.as_graph_def())
            frozen = tf.graph_util.convert_variables_to_constants(session, variable, output)
            return frozen

    tf.keras.backend.set_learning_phase(0)

    model = tf.keras.models.load_model(path_to_keras_model)

    session = tf.keras.backend.get_session()

    input_names = [layer.op.name for layer in model.inputs]
    output_names = [layer.op.name for layer in model.outputs]

    frozen_graph = _freeze_graph(session.graph, session, output_names)
    if save_dir:
        graph_io.write_graph(frozen_graph, save_dir, save_name, as_text=False)

    return frozen_graph, (input_names, output_names)


@timer("Inference time")
def write_inference_graph(frozen_graph, output_names, save_dir=None, save_name=None):

    trt_graph = trt.create_inference_graph(
        input_graph_def=frozen_graph,
        outputs=output_names,
        max_batch_size=1,
        max_workspace_size_bytes=1 << 25,
        precision_mode="FP16",
        minimum_segment_size=50
    )

    if save_dir and save_name:
        graph_io.write_graph(trt_graph, save_dir, save_name, as_text=False)

    return trt_graph
