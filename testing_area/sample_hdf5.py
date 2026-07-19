import h5py
import numpy as np

rng = np.random.default_rng(seed = 42)
matrix_data = rng.random((100, 100))
print(matrix_data)

# (Over-)Write to file
with h5py.File('testing_area/experiment_data.h5', 'w') as f:
    # Create a simple dataset
    f.create_dataset('sensor_1', data=matrix_data)

# accessing the file
with h5py.File('testing_area/experiment_data.h5', 'r') as f:
    # List all root-level datasets/groups
    print(list(f.keys()))  # Output: ['sensor_1']
    
    # Access the dataset object (does not load data yet)
    dset = f['sensor_1']
    print(dset.shape)  # Output: (100, 100)
    print(dset.dtype)  # Output: float64
    
    # Slice a specific chunk directly into a NumPy array
    # Cost less memory than loading the entire thing
    sub_array = dset[0:10, 0:10]
    print(sub_array)

# grouping
with h5py.File('testing_area/nested_data.h5', 'w') as f:
    # Create groups
    run_group = f.create_group('trial_1')
    sub_group = run_group.create_group('camera_data')
    
    # Save dataset inside the nested path
    sub_group.create_dataset('frames', data=np.zeros((10, 10)))
    
    # Alternative direct-path syntax:
    f['trial_1/camera_data/timestamps'] = np.arange(10)
    print(list(f.keys()))

with h5py.File('testing_area/nested_data.h5', 'r') as f:
    cam_data = f['trial_1/camera_data']
    print(list(cam_data.keys()))