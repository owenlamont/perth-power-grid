import numpy as np
import pandas as pd
import shapefile
from pathlib import Path

from multiprocessing import Process, Queue, freeze_support


#
# Function run by worker processes
#

def worker(input, output):
    for func, args in iter(input.get, 'STOP'):
        result = calculate(func, args)
        output.put(result)


#
# Function used to calculate result
#

def calculate(func, args):
    result = func(*args)
    return result


#
# Functions referenced by tasks
#

def read_vertices(shape_file: str) -> np.array:
    array_shapes = np.empty([1, 2])
    shape_reader = shapefile.Reader(str(shape_file))
    shapes = shape_reader.shapes()
    for i in range(len(shapes)):
        curr_coords = np.asarray(shapes[i].points)
        array_shapes = np.row_stack((array_shapes, curr_coords))
    return array_shapes


#
# Main test method
#

def test():
    # Directory of all shape files collected from https://catalogue.data.wa.gov.au/organization/western-power
    western_power_data = Path("../western_power")
    shape_file_list = list(western_power_data.glob("**/*.shp"))
    western_power_shape_list = [str(shape_file) for shape_file in shape_file_list]

    NUMBER_OF_PROCESSES = len(western_power_shape_list)
    TASKS = [(read_vertices, (file_name,)) for file_name in western_power_shape_list]

    # Create queues
    task_queue = Queue()
    done_queue = Queue()

    # Submit tasks
    for task in TASKS:
        task_queue.put(task)

    # Start worker processes
    for i in range(NUMBER_OF_PROCESSES):
        Process(target=worker, args=(task_queue, done_queue)).start()

    # Get and print results
    array_shapes = np.empty([1, 2])
    print('Unordered results:')
    for i in range(len(TASKS)):
        shape_array = done_queue.get()
        array_shapes = np.row_stack((array_shapes, shape_array))

    point_df = pd.DataFrame(data=array_shapes[1:, :], columns=['x', 'y'])
    point_df.to_parquet("point_data.gzip", compression='gzip')

    # Tell child processes to stop
    for i in range(NUMBER_OF_PROCESSES):
        task_queue.put('STOP')

    pass


if __name__ == '__main__':
    freeze_support()
    test()
