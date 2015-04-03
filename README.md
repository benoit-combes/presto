# Soda

Soda provides a little framework that aim to ease the writing of complex pipeline. It has originally been written for medical imaging processing purpose but can be used in any other domain. 

It has been tested only on Linux so far, it probably works on other Unix system, but not on Windows.

It requires to know python [regular expression](https://docs.python.org/3/library/re.html) and the [yaml](http://yaml.org/spec/1.1/#id857168) syntax for configuration files.

### Features:

- Meta representation of the data to process and pipelines. 
- Parallelism of each step of the pipeline over a number of maximum worker.
- Logging of the state of the whole process
- Interruption / resume of the whole process

### Usage:

In order to use soda you first have to write a yaml configuration file that will describe how your data/files? are organised on your computer.

Then you can write another yaml file to describe the different step of your pipeline or use one already written. 

Once those file are written you are ready to launch the pipeline.

##### Let's take an example:
We have the T1 and T2 contrasted MRI image of the brain of 2 patients at 3 timepoint. 

The goal of the pipeline is to denoised each of the images and then register the T1 images of the timepoints 2, and 3 on the T1 image of the first one.

our data are stored like this:

```
workspace/
├── patient_1
│   ├── timepoint_1
│   │   ├── T1.nrrd
│   │   └── T2.nrrd
│   ├── timepoint_2
│   │   ├── T1.nrrd
│   │   └── T2.nrrd
│   └── timepoint_3
│       ├── T1.nrrd
│       └── T2.nrrd
└── patient_2
    ├── timepoint_1
    │   ├── T1.nrrd
    │   └── T2.nrrd
    ├── timepoint_2
    │   ├── T1.nrrd
    │   └── T2.nrrd
    └── timepoint_3
        ├── T1.nrrd

```

To get representaion of your data Soda, use a mechanism of scopes. 
So, "describe  how your data/files? are organised on your computer", means tell to Soda where are store your files and how it can be "scoped". 

To acheive this the first thing to do is give the root directory of all our data. In our case it is `/workspace/`.

In a file "data_struct.yaml" we write:
```yaml
# ############################################################################
# MANDATORY --> __ROOT__ path
# ############################################################################

__ROOT__: /workspace/
```

All keys in the yaml documants that are prefixed and suffixed by tow underscores are mandatory for the proper functioning of Soda.
The value of the `__ROOT__` key, and any other key is a regular expression.

We now have to tell what are our scopes. In our case we first want to denoised all the images so the first scope that naturally comes in head is the set that include all the images which are nrrd files.

We had to the "data_struct.yaml" file:
```yaml
# ############################################################################
# MANDATORY --> __SCOPES__ structure
# ############################################################################
__SCOPES__:
  T1_AND_T2: \.nrrd
```

`__SCOPES__` is a key which takes as value a dictionnary where is key is the name of a scope and each associated value is a regular expression used to identify the scope. 

To identify the scope Soda list all the files inside the the root directory and keep the set of string composed by what match the corresponding regular expression and all that was before.

In the case of our `T1_TO_REGISTER` scope we want to match all The images. The set representing the scope will be simply the list of those files:
```py
{
    '/workspace/patient_2/timepoint_2/T1.nrrd',
    '/workspace/patient_2/timepoint_2/T2.nrrd',
    '/workspace/patient_2/timepoint_1/T1.nrrd',
    '/workspace/patient_2/timepoint_1/T2.nrrd',
    '/workspace/patient_2/timepoint_3/T1.nrrd',
    '/workspace/patient_2/timepoint_3/T2.nrrd',
    '/workspace/patient_1/timepoint_2/T1.nrrd',
    '/workspace/patient_1/timepoint_2/T2.nrrd',
    '/workspace/patient_1/timepoint_1/T1.nrrd',
    '/workspace/patient_1/timepoint_1/T2.nrrd',
    '/workspace/patient_1/timepoint_3/T1.nrrd',
    '/workspace/patient_1/timepoint_3/T2.nrrd',
}
```

Using this way of getting all the T1.nrrd and T2.nrrd images is dangerous:

If my pipeline create new file with nrrd extensions and if i want to launch my pipeline I will have to prune all the newly created file are thay will be processed as well. 

a better way would be: 
```yaml
# ############################################################################
# MANDATORY --> __SCOPES__ structure
# ############################################################################

T1: T1.nrrd 
T2: T2.nrrd

T1_AND_T2: (${T1}|${T2})

__SCOPES__:
  T1_AND_T2: ${T1_AND_T2}
```

All `KEY` framed with `${}` will be replaced by the corresponding string value inside this yaml document. you can nested and use it as many times as you want.

We know want to tell which scopes will be used for the registration step.
We want to register the T1 of the timepoint 2 and 3, so we need a scope that will return the following set:

```py
{
    '/workspace/patient_1/timepoint_2/',
    '/workspace/patient_1/timepoint_3/',
    '/workspace/patient_2/timepoint_2/',
    '/workspace/patient_2/timepoint_3/',
}
```

In order to do this we complete "data_struct.yaml" to add a new scope `T1_TO_REGISTER` wich will match the list above.
```yaml
T1: T1.nrrd 
T2: T2.nrrd

T1_AND_T2: (${T1}|${T2})
T1_TO_REGISTER: timepoint_(?!0)\d/

__SCOPES__:
  T1_AND_T2: ${T1_AND_T2}
  T1_TO_REGISTER: ${T1_TO_REGISTER}
```

We feel like if we have all of what we want so we will now start to write our pipeline. 

The pipeline is describe inside a yaml file, each yaml document (yaml document are separated by `---`) is a step of te pipeline

Each step must have the following keys:
```yaml
__DESCRIPTION__: "Denoised T1 and T2"
__SCOPE__: T1_AND_T2

__NAME__: denoise_t1_and_t2
__CMD__: 
```

- `__DESCRIPTION__` is  a descriptor of the step used to print the progression of the pipeline in a terminal.
- `__SCOPE__` is the scope inside where the step has to be perfomed.
- `__NAME__` is internally used to keep the avancedment of the pipeline in case of interruption.
- `__CMD__` is a list of all the arg of the command line that you want to be launched for that step.

for each of the step of the pipeline Soda will get the set corresponding to its scope and submit a new worker (i.e. a threadr which will launch the given command) for each element of the set.

The denoising process is perform using an execuatable called my_denoising, 
The usage of my_denoising is :

```
Usage:
    my_denoising <image_file_path>
```

We can complete `__CMD__`:
```yaml
__CMD__:
  - my_denoising
  - ?{T1_AND_T2}
```

All `KEY` framed with `?{}` will be replaced what match the regular expression given by the string value corresponding to KEY in the yaml document where the data structure is described in all the path of the files inside the current scope beeing processed. It must have only one match with the regular expression otherwise Soda will return an error for that step. 

example:
the set corresponding to the T1_AND_T2 scope is:
```py
{
    '/workspace/patient_2/timepoint_2/T1.nrrd',
    '/workspace/patient_2/timepoint_2/T2.nrrd',
    '[...]', 
}
```

so the first worker 


