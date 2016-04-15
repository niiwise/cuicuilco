#! /usr/bin/env python

#General purpose hierarchical network for data processing

#Changes: Improved multi-data function based training methods (+ graph based for SFA) (WIP)
#New more modularized version, with new three structure and node/signal cache  
#By Alberto Escalante. Alberto.Escalante@neuroinformatik.ruhr-uni-bochum.de First Version 9 Dec 2009
#Ruhr-University-Bochum, Institute of Neurocomputation, Group of Prof. Dr. Wiskott

#TODO: write correct interface to enable for excecution_read, excecution_save
#also, check integer from float arguments in parallelization

#USAGE EXAMPLE: python cuicuilco_run.py --Experiment=ParamsNatural --Network=u08expoNetwork1L --InputFilename=/scratch/escalafl/cooperations/igel/rbm_64/data_bin_4000.bin --OutputFilename=deleteme2.txt

import numpy
import scipy
import matplotlib as mpl
mpl.use('Qt4Agg')
import matplotlib.pyplot as plt
import PIL
###import Image
import mdp
import more_nodes
import patch_mdp

import object_cache as cache
import os, sys
import glob
import random
import sfa_libs
from sfa_libs import (scale_to, distance_squared_Euclidean, str3, wider_1Darray, ndarray_to_string, cutoff)
from exact_label_learning import (ConstructGammaFromLabels, RemoveNegativeEdgeWeights, MapGammaToEdgeWeights)
import SystemParameters
from SystemParameters import (scale_sSeq, take_first_02D, take_0_k_th_from_2D_list, sSeq_force_image_size, sSeq_getinfo_format, convert_sSeq_to_funcs_params_sets)
from imageLoader import *
import classifiers_regressions as classifiers
import network_builder
import time
from matplotlib.ticker import MultipleLocator
import copy
import string
from nonlinear_expansion import (identity, pair_prod_adj1_ex, pair_prod_adj2_ex, QE, TE)
import getopt
from lockfile import LockFile
import mkl
mkl.set_num_threads(22)
from inspect import getmembers

#from mdp import numx
#sys.path.append("/home/escalafl/workspace/hiphi/src/hiphi/utils")
#import misc
#import cache

#from SystemParameters import *
#list holding the benchmark information with entries: ("description", time as float in seconds)
benchmark=[]


t0 = time.time()
print "LOADING INPUT INFORMATION"        

random_seed = 123456
numpy.random.seed(random_seed)

enable_display = False
input_filename = None
output_filename = None
cache_available = True
network_cache_read_dir = None #"/local/tmp/escalafl/Alberto/SavedNetworks"
network_cache_write_dir = None #"/local/tmp/escalafl/Alberto/SavedNetworks"
node_cache_read_dir = None #"/local/tmp/escalafl/Alberto/SavedNodes"
node_cache_write_dir = None #"/local/tmp/escalafl/Alberto/SavedNodes"
signal_cache_read_dir = None #"/local/tmp/escalafl/Alberto/SavedSignals"
signal_cache_write_dir = None #"/local/tmp/escalafl/Alberto/SavedSignals"
classifier_cache_read_dir = None #"/local/tmp/escalafl/Alberto/SavedClassifiers"
classifier_cache_write_dir = None #"/local/tmp/escalafl/Alberto/SavedClassifiers"

enable_command_line = True
reg_num_signals = 4
skip_num_signals = 0
use_full_sl_output = False
enable_kNN=False
enable_NCC=False
enable_GC=False
kNN_k = 1
enable_svm=False
svm_gamma = 0
svm_C = 1.0
svm_min = -1.0 
svm_max = 1.0
enable_lr = False
load_network_number = None
ask_network_loading = True
#network_base_dir = None #"/local/tmp/escalafl/Alberto/SavedNetworks"
n_parallel = None # 5
enable_scheduler = False

save_subimages_training = False #or True
save_images_training_supplementary_info = None
save_average_subimage_training = False #or True
save_sorted_AE_Gauss_newid = False #or True
save_sorted_incorrect_class_Gauss_newid = False #or True
compute_slow_features_newid_across_net = 0 #or 1,2,3
estimate_explained_var_with_inverse = False
estimate_explained_var_with_kNN_k = 0
estimate_explained_var_with_kNN_lin_app_k = 0
estimate_explained_var_linear_global_N = 0
add_normalization_node = False
make_last_PCA_node_whithening=False
feature_cut_off_level = 0.0
use_filter = None
export_data_to_libsvm = False
integer_label_estimation = False
cumulative_scores = False
confusion_matrix = False
features_residual_information  = 5000 #0
compute_input_information = True
convert_labels_days_to_years = False

clip_seenid_newid_to_training = False
add_noise_to_seenid=False

dataset_for_display_train = 0
dataset_for_display_newid = 0

graph_exact_label_learning = False
output_instead_of_SVM2 = False
number_of_target_labels_per_orig_label=0 #The total number of labels is num_orig_labels * number_of_target_labels_per_orig_label

coherent_seeds=False or True

cuicuilco_queue = "/home/escalafl/workspace4/cuicuilco_MDP3.2/src/queue_cuicuilco.txt"
cuicuilco_lock_file = "/home/escalafl/workspace4/cuicuilco_MDP3.2/src/queue_cuicuilco"
minutes_sleep = 0

import hierarchical_networks
import experiment_datasets
print "Using mdp version:", mdp.__version__, "file:", mdp.__file__
print hierarchical_networks.__file__
print experiment_datasets.__file__

available_experiments = {}
print "Creating list of available experiments:"
for (obj_name, obj_value) in getmembers(experiment_datasets):
    if isinstance(obj_value, SystemParameters.ParamsSystem):
        print "   ", obj_name
        available_experiments[obj_name] = obj_value
#        print "object", obj.__name__

available_networks = {}
print "Creating list of available networks:"
for (obj_name, obj_value) in getmembers(hierarchical_networks):
    if isinstance(obj_value, SystemParameters.ParamsNetwork) and obj_name != "network":
        print "   ", obj_name
        available_networks[obj_name] = obj_value
#        print "object", obj.__name__

name_default_experiment = "ParamsMNISTFunc"
name_default_network = "voidNetwork1L"

DefaultExperimentDataset = available_experiments[name_default_experiment]
DefaultNetwork = available_networks[name_default_network]

    #This defines the sequences used for training, and testing
    #See also: ParamsGender, ParamsAngle, ParamsIdentity,  ParamsTransX, ParamsAge,  
    #ParamsRTransX, ParamsRTransY, ParamsRScale, ParamsRFace, ParamsRObject, ParamsNatural, ParamsRawNatural
    #ParamsRFaceCentering, ParamsREyeTransX, ParamsREyeTransY
    #Data Set based training data: ParamsRTransXFunc, ParamsRTransYFunc, ParamsRTransXY_YFunc
    #ParamsRGTSRBFunc, ParamsRAgeFunc, ParamsMNISTFunc
#from experiment_datasets import ParamsMNISTFunc as DefaultExperimentDataset #ParamsRAgeFunc, ParamsMNISTFunc
# ParamsRTransXYScaleFunc

    # Networks available: voidNetwork1L, SFANetwork1L, PCANetwork1L, u08expoNetwork1L, quadraticNetwork1L
    # Test_Network, linearNetwork4L, u08expoNetwork4L, NL_Network5L, linearNetwork5L, linearNetworkT6L, TestNetworkT6L, 
    # linearNetworkU11L, TestNetworkU11L, nonlinearNetworkU11L, TestNetworkPCASFAU11L, linearPCANetworkU11L,  u08expoNetworkU11L 
    # linearWhiteningNetwork11L, u08expo_m1p1_NetworkU11L, u08expoNetworkU11L, experimentalNetwork
    # u08expo_pcasfaexpo_NetworkU11L, u08expoA2NetworkU11L/A3/A4, u08expoA3_pcasfaexpo_NetworkU11L, IEMNetworkU11L, SFANetwork1LOnlyTruncated
#from hierarchical_networks import NLIPCANetwork1L as DefaultNetwork ### using A4 lately, u08expoNetworkU11L, u08expo_pcasfaexpo_NetworkU11L, u08expoNetwork2T
#GTSRBNetwork, u08expoNetworkU11L, u08expoS42NetworkU11L, u08expoNetwork1L, HeuristicEvaluationExpansionsNetworkU11L, HeuristicPaperNetwork
#HeuristicEvaluationExpansionsNetworkU11L, HardSFAPCA_u08expoNetworkU11L, HardSFAPCA_u08expoNetworkU11L
#GTSRBNetwork, u08expoNetworkU11L, IEVMLRecNetworkU11L, linearPCANetworkU11L, SFAAdaptiveNLNetwork32x32U11L, 
#u08expoNetwork32x32U11L_NoTop
#5x5L0 Networks: u08expoNetworkU11L_5x5L0, linearPCANetworkU11L_5x5L0, IEVMLRecNetworkU11L_5x5L0, PCANetwork1L
# MNISTNetwork7L, SFANetwork1LOnlyTruncated, MNISTNetwork_24x24_7L, MNISTNetwork_24x24_7L_B, SFANetworkMNIST2L, (MNIST 8C:) SFANetwork1L, SFADirectNetwork1L (MNIST: semi-supervised, Gender: exact label)
# GENDER ELL: NetworkGender_8x8L0
# AGE MORPH-II: IEVMLRecNetworkU11L_Overlap6x6L0_1Label, HeadNetwork1L, IEVMLRecNetworkU11L_Overlap6x6L0_GUO_3Labels, IEVMLRecNetworkU11L_Overlap6x6L0_GUO_1Label, SFANetworkU11L_Overlap6x6L0_GUO_3Labels
# IEVMLRecNetworkU11L_Overlap6x6L0_3Labels <-Article HiGSFA, IEVMLRecNetworkU11L_Overlap6x6L0_2Labels

#TT4 PCANetwork
#u08expoS42NetworkU11L
from experiment_datasets import experiment_seed
from experiment_datasets import DAYS_IN_A_YEAR

if coherent_seeds:
    print "experiment_datasets.experiment_seed=", experiment_seed
    numpy.random.seed(experiment_seed+111111)

if enable_command_line:
    argv = None
    if argv is None:
        argv = sys.argv
    print "Apparent command line arguments: \n", " ".join(argv)
    if len(argv) >= 2:
        try:
            opts, args = getopt.getopt(argv[1:], "", ["Experiment=", "InputFilename=", "EnableDisplay=", "WriteSlowness=", "OutputFilename=", 
                                                      "CacheAvailable=", "NumFeaturesSup=", "SkipFeaturesSup=",
                                                      'SVM_gamma=', 'SVM_C=','EnableSVM=', "LoadNetworkNumber=", "AskNetworkLoading=",
                                                      'EnableLR=', "NParallel=", "EnableScheduler=",
                                                      "NetworkCacheReadDir=", "NetworkCacheWriteDir=", "NodeCacheReadDir=", "NodeCacheWriteDir=",
                                                      "SignalCacheReadDir=", "SignalCacheWriteDir=", "ClassifierCacheReadDir=", 
                                                      "ClassifierCacheWriteDir=", "SaveSubimagesTraining=",  "SaveAverageSubimageTraining=",
                                                      "SaveSorted_AE_GaussNewid=", "SaveSortedIncorrectClassGaussNewid=", 
                                                      "ComputeSlowFeaturesNewidAcrossNet=", "UseFilter=", "kNN_k=",'EnableKNN=', "EnableNCC=", 
                                                      "EnableGC=", "SaveSubimagesTrainingSupplementaryInfo=", "EstimateExplainedVarWithInverse=",
                                                      "EstimateExplainedVarWithKNN_k=", "EstimateExplainedVarWithKNNLinApp_k=", 
                                                      "EstimateExplainedVarLinGlobal_N=", "AddNormalizationNode=", 
                                                      "MakeLastPCANodeWhithening=", "FeatureCutOffLevel=", "ExportDataToLibsvm=",
                                                      "IntegerLabelEstimation=", "CumulativeScores=", "FeaturesResidualInformation=", 
                                                      "ComputeInputInformation=", "SleepM=", "DatasetForDisplayTrain=", "DatasetForDisplayNewid=",
                                                      "GraphExactLabelLearning=", "OutputInsteadOfSVM2=", "NumberTargetLabels=", "ConfusionMatrix=",
                                                      "MapDaysToYears=", "AddNoiseToSeenid=", "ClipSeenidNewid=",
                                                      "HierarchicalNetwork=", "ExperimentDataset="])            
            print "opts=", opts
            print "args=", args

            if len(args)>0:
                print "Arguments not understood:", args
                sys.exit(2)
                               
            for opt, arg in opts:
#                print "opt=", opt
#                print "arg=", arg
#TODO: Dictionary with name/experiment in experiment_datasets
                if opt in ('--Experiment'):
                    if arg == "ParamsNatural":
                        #make this a function?
                        from experiment_datasets import ParamsNatural as DefaultExperimentDataset
                    elif arg == "ParamsRawNatural":
                        from experiment_datasets import ParamsRawNatural as DefaultExperimentDataset                        
                    else:
                        print "Unknown experiment:", arg
                        sys.exit(2)
                    print "Setting Parameters=", DefaultExperimentDataset.name
                elif opt in ('--InputFilename'):
                    input_filename = arg
                    print "Using the following input file:", input_filename
                elif opt in ('--OutputFilename'):
                    output_filename = arg
                    print "Using the following output file:", output_filename
                elif opt in ('--WriteSlowness'):
                    if arg == '1':
                        write_slowness = True
                    else:
                        write_slowness = False
                    print "Setting write_slowness to", write_slowness   
                elif opt in ('--EnableDisplay'):
                    if arg == '1':
                        enable_display=True
                    else:
                        enable_display=False
                    print "Setting enable_display to", enable_display      
                elif opt in ('--CacheAvailable'):
                    if arg == '1':
                        cache_available=True
                    else:
                        cache_available=False             
                    print "Setting cache_available to", cache_available               
                elif opt in ('--NumFeaturesSup'):
                    reg_num_signals = int(arg)
                    print "Setting reg_num_signals to", reg_num_signals
                elif opt in ('--SkipFeaturesSup'):
                    skip_num_signals = int(arg)
                    print "Setting skip_num_signals to", skip_num_signals
                elif opt in ('--SVM_gamma'):
                    svm_gamma = float(arg)
                    print "Setting svm_gamma to", svm_gamma   
                elif opt in ('--SVM_C'):
                    svm_C = float(arg)
                    print "Setting svm_C to", svm_C   
                elif opt in ('--EnableSVM'):
                    enable_svm = int(arg)
                    print "Setting enable_svm to", enable_svm   
                elif opt in ('--LoadNetworkNumber'):
                    load_network_number = int(arg)
                    print "Setting load_network_number to", load_network_number 
                elif opt in ('--AskNetworkLoading'):
                    ask_network_loading = int(arg)
                    print "Setting ask_network_loading to", ask_network_loading    
                elif opt in ('--EnableLR'):
                    enable_lr = int(arg)
                    print "Setting enable_lr to", enable_lr   
#                elif opt in ('--NetworkBaseDir'):
#                    network_base_dir = arg
#                    print "Setting network_base_dir to", network_base_dir 
                elif opt in ('--NParallel'):
                    n_parallel = int(arg)
                    print "Setting n_parallel to", n_parallel   
                elif opt in ('--EnableScheduler'):
                    enable_scheduler = int(arg)             
                    print "Setting enable_scheduler to", enable_scheduler   
                elif opt in ('--NetworkCacheReadDir'):
                    if arg == "None":
                        network_cache_read_dir = None
                    else:
                        network_cache_read_dir = arg
                    print "Setting network_cache_read_dir to", network_cache_read_dir 
                elif opt in ('--NetworkCacheWriteDir'):
                    if arg == "None":
                        network_cache_write_dir = None
                    else:
                        network_cache_write_dir = arg
                    print "Setting network_cache_write_dir to", network_cache_write_dir
                elif opt in ('--NodeCacheReadDir'):
                    if arg == "None":
                        node_cache_read_dir = None
                    else:
                        node_cache_read_dir = arg
                    print "Setting node_cache_read_dir to", node_cache_read_dir       
                elif opt in ('--NodeCacheWriteDir'):
                    if arg == "None":
                        node_cache_write_dir = None
                    else:
                        node_cache_write_dir = arg
                    print "Setting node_cache_write_dir to", node_cache_write_dir       
                elif opt in ('--SignalCacheReadDir'):
                    if arg == "None":
                        signal_cache_read_dir = None
                    else:
                        signal_cache_read_dir = arg
                    print "Setting signal_cache_read_dir to", signal_cache_read_dir
                elif opt in ('--SignalCacheWriteDir'):
                    if arg == "None":
                        signal_cache_write_dir = None
                    else:
                        signal_cache_write_dir = arg
                    print "Setting signal_cache_write_dir to", signal_cache_write_dir       
                elif opt in ('--ClassifierCacheReadDir'):
                    if arg == "None":
                        classifier_cache_read_dir = None
                    else:
                        classifier_cache_read_dir = arg
                    print "Setting classifier_cache_read_dir to", classifier_cache_read_dir       
                elif opt in ('--ClassifierCacheWriteDir'):
                    if arg == "None":
                        classifier_cache_write_dir = None
                    else:
                        classifier_cache_write_dir = arg
                    print "Setting classifier_cache_write_dir to", classifier_cache_write_dir   
                elif opt in ('--SaveSubimagesTraining'):
                    save_subimages_training = bool(int(arg))
                    print "Setting save_subimages_training to", save_subimages_training
                elif opt in ('--SaveAverageSubimageTraining'):
                    save_average_subimage_training = bool(int(arg)) 
                    print "Setting save_average_subimage_training to", save_average_subimage_training
                elif opt in ('--SaveSorted_AE_GaussNewid'):
                    save_sorted_AE_Gauss_newid = bool(int(arg)) 
                    print "Setting save_sorted_AE_Gauss_newid to", save_sorted_AE_Gauss_newid
                elif opt in ('--SaveSortedIncorrectClassGaussNewid'):
                    save_sorted_incorrect_class_Gauss_newid = bool(int(arg)) 
                    print "Setting save_sorted_incorrect_class_Gauss_newid to", save_sorted_incorrect_class_Gauss_newid 
                elif opt in ('--ComputeSlowFeaturesNewidAcrossNet'):
                    compute_slow_features_newid_across_net = int(arg) 
                    print "Setting compute_slow_features_newid_across_net to", compute_slow_features_newid_across_net
                elif opt in ('--UseFilter'):
                    use_filter = arg 
                    print "Setting use_filter to",  use_filter
                elif opt in ('--kNN_k'):
                    kNN_k = int(arg) 
                    print "Setting kNN_k to", kNN_k
                elif opt in ('--EnableKNN'):
                    enable_kNN = bool(int(arg)) 
                    print "Setting enable_kNN to", enable_kNN
                elif opt in ('--EnableNCC'):
                    enable_NCC = bool(int(arg)) 
                    print "Setting enable_NCC to", enable_NCC
                elif opt in ('--EnableGC'):
                    enable_GC = bool(int(arg)) 
                    print "Setting enable_GC to", enable_GC
                    print "WARNING: This option only modifies regression display for now"
                elif opt in ('--SaveSubimagesTrainingSupplementaryInfo'):
                    save_images_training_supplementary_info = arg 
                    print "Setting save_images_training_supplementary_info to", save_images_training_supplementary_info       
                    #quit()   
                elif opt in ('--EstimateExplainedVarWithInverse'):
                    estimate_explained_var_with_inverse = bool(int(arg))
                    print "Setting estimate_explained_var_with_inverse to", estimate_explained_var_with_inverse
                elif opt in ('--EstimateExplainedVarWithKNN_k'):
                    estimate_explained_var_with_kNN_k = int(arg)
                    print "Setting estimate_explained_var_with_kNN_k to", estimate_explained_var_with_kNN_k
                elif opt in ('--EstimateExplainedVarWithKNNLinApp_k'):
                    estimate_explained_var_with_kNN_lin_app_k = int(arg)
                    print "Setting estimate_explained_var_with_kNN_lin_app_k to", estimate_explained_var_with_kNN_lin_app_k
                elif opt in ('--EstimateExplainedVarLinGlobal_N'):
                    estimate_explained_var_linear_global_N = int(arg)
                    print "Setting estimate_explained_var_linear_global_N to", estimate_explained_var_linear_global_N
                elif opt in ('--AddNormalizationNode'):
                    add_normalization_node = bool(int(arg))
                    print "Setting add_normalization_node to", add_normalization_node                    
                elif opt in ('--MakeLastPCANodeWhithening'):
                    make_last_PCA_node_whithening = bool(int(arg))
                    print "Setting make_last_PCA_node_whithening to", make_last_PCA_node_whithening              
                elif opt in ('--FeatureCutOffLevel'):
                    feature_cut_off_level = float(arg)
                    print "Setting feature_cut_off_level to", feature_cut_off_level
                elif opt in ('--ExportDataToLibsvm'):
                    export_data_to_libsvm = bool(int(arg))
                    print "Setting export_data_to_libsvm to", export_data_to_libsvm
                elif opt in ('--IntegerLabelEstimation'):
                    integer_label_estimation = bool(int(arg))
                    print "Setting integer_label_estimation to", integer_label_estimation
                elif opt in ('--CumulativeScores'):
                    cumulative_scores = bool(int(arg))
                    print "Setting cumulative_scores to", cumulative_scores
                elif opt in ('--FeaturesResidualInformation'):
                    features_residual_information = int(arg)
                    print "Setting features_residual_information to", features_residual_information
                elif opt in ('--ComputeInputInformation'):
                    compute_input_information = bool(int(arg))
                    print "Setting compute_input_information to", compute_input_information                
                elif opt in ('--SleepM'):
                    minutes_sleep = float(arg)
                    if minutes_sleep >= 0:
                        print "Sleeping for %f minutes..."%minutes_sleep
                        time.sleep(minutes_sleep*60)
                        print "... and awoke"
                    else:
                        print "Sleeping until execution in cuicuilco queue"
                        t_wa = time.time()
                        lock = LockFile(cuicuilco_lock_file)
                        pid = os.getpid()
                        print "process pid is:", pid
                        #Add this proces to the queue
                        print "adding process to queue..."
                        lock.acquire()
                        q = open(cuicuilco_queue , "a")
                        q.write("%d\n"%pid)
                        q.close()
                        lock.release()
                        served = False
                        while not served:                                                                         
                            lock.acquire()
                            q = open(cuicuilco_queue, "r")
                            next_pid = int(q.readline())
                            print "top of queue:", next_pid,
                            q.close()
                            lock.release()

                            if next_pid == pid:
                                print "our turn in queue"
                                served = True
                            else:
                                print "sleeping 60 seconds"
                                time.sleep(60) #sleep for 10 seconds
                        t_wb = time.time()
                        print "process is executing now. Total waiting time: %f min"%((t_wb-t_wa)/60.0)
                        #print "waiting for 35 minutes!!!"
                        #time.sleep(60*35) 
                elif opt in ('--DatasetForDisplayTrain'):
                    dataset_for_display_train = int(arg)
                    print "Setting dataset_for_display_train to", dataset_for_display_train
                elif opt in ('--DatasetForDisplayNewid'):
                    dataset_for_display_newid = int(arg)
                    print "Setting dataset_for_display_newid to", dataset_for_display_newid
                elif opt in ('--GraphExactLabelLearning'):
                    graph_exact_label_learning = bool(int(arg))
                    print "Setting graph_exact_label_learning to", graph_exact_label_learning
                elif opt in ('--OutputInsteadOfSVM2'):
                    output_instead_of_SVM2 = bool(int(arg))
                    print "Setting output_instead_of_SVM2 to", output_instead_of_SVM2
                elif opt in ('--NumberTargetLabels'):
                    number_of_target_labels_per_orig_label = int(arg)
                    print "Setting number_of_target_labels_per_orig_label to", number_of_target_labels_per_orig_label
                elif opt in ('--ConfusionMatrix'):
                    confusion_matrix = bool(int(arg))
                    print "Setting confusion_matrix to", confusion_matrix                     
                elif opt in ('--MapDaysToYears'):
                    convert_labels_days_to_years = bool(int(arg))
                    print "Setting convert_labels_days_to_years to", convert_labels_days_to_years                
                elif opt in ('--AddNoiseToSeenid'):
                    add_noise_to_seenid = bool(int(arg))
                    print "Setting add_noise_to_seenid to", add_noise_to_seenid                
                elif opt in ('--ClipSeenidNewid'):
                    clip_seenid_newid_to_training = bool(int(arg))
                    print "Setting clip_seenid_newid_to_training to", clip_seenid_newid_to_training      
                elif opt in ('--HierarchicalNetwork'):
                    name_default_network = arg
                    print "Setting default_network to", name_default_network       
                    DefaultNetwork = available_networks[name_default_network]
                elif opt in ('--ExperimentDataset'):
                    name_default_experiment = arg
                    print "Setting name_default_experiment to", name_default_experiment   
                    DefaultExperimentDataset = available_experiments[name_default_experiment]
                else:
                    print "Argument not handled: ", opt
                    quit()
        except getopt.GetoptError:
            print "Error parsing the arguments: ", argv[1:]
            sys.exit(2)

if enable_svm:
    import svm as libsvm


if coherent_seeds:
    print "experiment_datasets.experiment_seed=", experiment_seed
    numpy.random.seed(experiment_seed+12121212)

if enable_scheduler and n_parallel > 1:
    scheduler = mdp.parallel.ThreadScheduler(n_threads=n_parallel)
else:
    scheduler = None

if features_residual_information <= 0 and compute_input_information:
    print "ignoring flag compute_input_information=%d because  features_residual_information=%d <= 0"%(compute_input_information,features_residual_information)
    compute_input_information = False
    
Parameters = DefaultExperimentDataset
Network = DefaultNetwork

#Peculiarities for specifying the ParamsNatural experiment (requires run-time computations)
if Parameters == experiment_datasets.ParamsNatural and input_filename != None:
    (magic_num, iteration, numSamples, rbm_sfa_numHid, sampleSpan) = read_binary_header("", input_filename)
    print "Iteration Number=%d,"%iteration, "numSamples=%d"%numSamples,"rbm_sfa_numHid=%d,"%rbm_sfa_numHid
    
    Parameters.sTrain.subimage_width = rbm_sfa_numHid / 8
    Parameters.sTrain.subimage_height = rbm_sfa_numHid / Parameters.sTrain.subimage_width
    Parameters.sTrain.name = "RBM Natural. 8x8 (exp 64=%d), iter %d, num_images %d"%(rbm_sfa_numHid, iteration, Parameters.sTrain.num_images)
    Parameters.sSeenid.subimage_width = rbm_sfa_numHid / 8
    Parameters.sSeenid.subimage_height = rbm_sfa_numHid / Parameters.sSeenid.subimage_width
    Parameters.sSeenid.name = "RBM Natural. 8x8 (exp 64=%d), iter %d, num_images %d"%(rbm_sfa_numHid, iteration, Parameters.sSeenid.num_images)
    Parameters.sNewid.subimage_width = rbm_sfa_numHid / 8
    Parameters.sNewid.subimage_height = rbm_sfa_numHid / Parameters.sNewid.subimage_width
    Parameters.sNewid.name = "RBM Natural. 8x8 (exp 64=%d), iter %d, num_images %d"%(rbm_sfa_numHid, iteration, Parameters.sNewid.num_images)

    Parameters.sTrain.data_base_dir = Parameters.sSeenid.data_base_dir = Parameters.sNewid.data_base_dir = ""
    Parameters.sTrain.base_filename = Parameters.sSeenid.base_filename = Parameters.sNewid.base_filename = input_filename

    if numSamples != 5000:
        er = "wrong number of Samples %d, 5000 were assumed"%numSamples
        raise Exception(er)

#quit()
#Cutoff for final network output
min_cutoff = -10 # -1.0e200, -30.0
max_cutoff = 10 # 1.0e200, 30.0

enable_reduced_image_sizes = Parameters.enable_reduced_image_sizes
reduction_factor =  Parameters.reduction_factor
hack_image_size =  Parameters.hack_image_size
enable_hack_image_size =  Parameters.enable_hack_image_size

#enable_reduced_image_sizes = False
if enable_reduced_image_sizes:
#    reduction_factor = 2.0 # (the inverse of a zoom factor)
    Parameters.name = Parameters.name + "_Resized images"
    for iSeq in (Parameters.iTrain, Parameters.iSeenid, Parameters.iNewid): 
        # iSeq.trans = iSeq.trans / 2
        pass

    for sSeq in (Parameters.sTrain, Parameters.sSeenid, Parameters.sNewid): 
        print "sSeq", sSeq
        if isinstance(sSeq, list):
            for i, sSeq_vect in enumerate(sSeq):
                print "sSeq_vect", sSeq_vect
                if sSeq_vect != None:
                    for j, sSeq_entry in enumerate(sSeq_vect):
                        if isinstance(sSeq_entry, SystemParameters.ParamsDataLoading):
                            #TODO: Avoid code repetition, even though readability compromised
                            scale_sSeq(sSeq_entry, reduction_factor)
                        else:
                            er = "Unexpected data structure"
                            raise Exception(er)
        else:
            scale_sSeq(sSeq, reduction_factor)

if coherent_seeds:
    numpy.random.seed(experiment_seed+34343434)

iTrain_set = Parameters.iTrain
sTrain_set = Parameters.sTrain
iTrain = take_0_k_th_from_2D_list(iTrain_set, k=dataset_for_display_train)
sTrain = take_0_k_th_from_2D_list(sTrain_set, k=dataset_for_display_train)

#TODO: take k=1? or choose from command line? NOPE. Take always first label. sSeq must compute proper classes for chosen label anyway.
objective_label = 1
if graph_exact_label_learning:
    if isinstance(iTrain_set, list):
        iTrain0 = iTrain_set[len(iTrain_set)-1][0]
    else:
        iTrain0 = take_0_k_th_from_2D_list(iTrain_set, k=0)
    Q = iTrain0.num_images

    if len(iTrain0.correct_labels.shape)==2:
        num_orig_labels = iTrain0.correct_labels.shape[1]
    else:
        num_orig_labels = 1
        iTrain0.correct_labels.reshape((-1,num_orig_labels))
        
    #number_of_target_labels_per_orig_label = 2 #1 or more for auxiliary labels
    if number_of_target_labels_per_orig_label >= 1:
        min_label = iTrain0.correct_labels.min(axis=0)
        max_label = iTrain0.correct_labels.max(axis=0)
        plain_labels = iTrain0.correct_labels.reshape((-1,num_orig_labels))
        num_samples = len(plain_labels)          
        auxiliary_labels = numpy.zeros((num_samples, num_orig_labels * number_of_target_labels_per_orig_label))
        auxiliary_labels[:,0:num_orig_labels] = plain_labels
        for i in range(1,number_of_target_labels_per_orig_label):
            auxiliary_labels[:,i*num_orig_labels:(i+1)*num_orig_labels] = numpy.cos((plain_labels-min_label) * (1.0+i)*numpy.pi / (max_label-min_label))
        print auxiliary_labels
    else:
        auxiliary_labels = iTrain0.correct_labels.reshape((-1,num_orig_labels))
        
    print "iTrain0.correct_labels.shape", iTrain0.correct_labels.shape
    orig_train_label_min = auxiliary_labels[:,objective_label].min()
    orig_train_label_max = auxiliary_labels[:,objective_label].max()   

    orig_train_labels_mean = numpy.array(auxiliary_labels).mean(axis=0)
    orig_train_labels_std = numpy.array(auxiliary_labels).std(axis=0)   
    orig_train_label_mean = orig_train_labels_mean[objective_label]
    orig_train_label_std = orig_train_labels_std[objective_label]

    orig_train_labels = auxiliary_labels
    orig_train_labels_mean = numpy.array(orig_train_labels).mean(axis=0)
    orig_train_labels_std = numpy.array(orig_train_labels).std(axis=0)   
    train_feasible_labels = (orig_train_labels - orig_train_labels_mean)/orig_train_labels_std
    print "original feasible (perhaps correlated) label.T: ", train_feasible_labels.T
    
    if len(iTrain0.correct_labels.shape)==2:
        iTrain0.correct_labels = iTrain0.correct_labels[:,objective_label].flatten()
        Parameters.iSeenid.correct_labels = Parameters.iSeenid.correct_labels[:,objective_label].flatten()
        Parameters.iNewid[0][0].correct_labels = Parameters.iNewid[0][0].correct_labels[:,objective_label].flatten()
        
        iTrain0.correct_classes = iTrain0.correct_classes[:,objective_label].flatten()
        Parameters.iSeenid.correct_classes = Parameters.iSeenid.correct_classes[:,objective_label].flatten()
        Parameters.iNewid[0][0].correct_classes = Parameters.iNewid[0][0].correct_classes[:,objective_label].flatten()

    
    node_weights = numpy.ones(Q)
    Gamma = ConstructGammaFromLabels(train_feasible_labels, node_weights, constant_deltas=False)        
    print "Resulting Gamma is", Gamma
    Gamma = RemoveNegativeEdgeWeights(node_weights, Gamma)
    print "Removed negative weighs. Gamma=", Gamma
#    edge_weights = MapGammaToEdgeWeights(Gamma) 
    edge_weights = Gamma

    if isinstance(sTrain_set, list):
        sTrain0 = sTrain_set[len(sTrain_set)-1][0]
    else:
        sTrain0 = take_0_k_th_from_2D_list(sTrain_set, k=0)
    
    sTrain0.train_mode = "graph"
    sTrain0.node_weights = node_weights
    sTrain0.edge_weights = edge_weights
     
    
print "sTrain=", sTrain
#quit()

iSeenid = Parameters.iSeenid
sSeenid = Parameters.sSeenid

if coherent_seeds:
    print "Setting coherent seed"
    numpy.random.seed(experiment_seed+56565656)

iNewid_set = Parameters.iNewid
sNewid_set = Parameters.sNewid
print "dataset_for_display_newid=", dataset_for_display_newid
iNewid = take_0_k_th_from_2D_list(iNewid_set, k=dataset_for_display_newid)
sNewid = take_0_k_th_from_2D_list(sNewid_set, k=dataset_for_display_newid)

#print "sNewid=", sNewid

##For displaying purposes only first entry in training sequences
#if isinstance(iTrain, list):
#    image_files_training = iTrain[0][0].input_files
#    num_images_training = num_images = iTrain[0][0].num_images
#else:
image_files_training = iTrain.input_files
#print image_files_training

num_images_training = num_images = iTrain.num_images

seq_sets = sTrain_set
seq = sTrain

#oTrain = NetworkOutput()

#WARNING!!!!!!!
#Move this after network loadings
hack_image_sizes = [135, 90, 64, 32, 16]
#Warning!!! hack_image_size = False




#hack_image_size = 64
#enable_hack_image_size = True
if enable_hack_image_size:
    sSeq_force_image_size(sTrain_set, hack_image_size, hack_image_size)
    sSeq_force_image_size(sSeenid, hack_image_size, hack_image_size)
    sSeq_force_image_size(sNewid_set, hack_image_size, hack_image_size)


        
subimage_shape, max_clip, signals_per_image, in_channel_dim = sSeq_getinfo_format(sTrain)

  
#Filter used for loading images with transparent background
#filter = generate_color_filter2((seq.subimage_height, seq.subimage_width))
if use_filter == "ColoredNoise" or use_filter == "1":
    alpha = 4.0 # mask 1 / f^(alpha/2) => power 1/f^alpha
    filter = filter_colored_noise2D_imp((seq.subimage_height, seq.subimage_width), alpha)
#back_type = None
#filter = None
elif use_filter=="None" or use_filter==None or use_filter == "0":
    filter = None
else:
    print "Unknown filter: ", use_filter
    quit()
sTrain.filter = filter
sSeenid.filter = filter
sNewid.filter = filter
        
#TODO: CREATE USER INTERFACE: users should be able to select a trained network, or train a new one
#                             and to set the training variables: type of training
#                             Also, users should set the analysis parameters: num. of signals 

#Work in process, for now keep cache disabled
network_read_enabled = True #and False
if network_read_enabled and cache_available:
    network_read = cache.Cache(network_cache_read_dir, "")
else:
    network_read = None



#Make this a parameter
network_saving_enabled = True #and False
if network_saving_enabled and cache_available and (network_cache_write_dir != None):
    network_write = cache.Cache(network_cache_write_dir, "")
else:
    network_write = None
    #print "bug", network_saving_enabled,cache_available,network_cache_write_dir
    #quit()
    
node_cache_read_enabled = True #and False
if node_cache_read_enabled and cache_available and (node_cache_read_dir != None):
    node_cache_read = cache.Cache(node_cache_read_dir, "")
else:
    node_cache_read = None
    
signal_cache_read_enabled = True #and False
if signal_cache_read_enabled and cache_available and (signal_cache_read_dir != None):
    signal_cache_read = cache.Cache(signal_cache_read_dir, "")
else:
    signal_cache_read = None

node_cache_write_enabled = True
if node_cache_write_enabled and cache_available and (node_cache_write_dir != None):
    node_cache_write = cache.Cache(node_cache_write_dir, "")
else:
    node_cache_write = None

signal_cache_write_enabled = True #and False #or network_saving_enabled
if signal_cache_write_enabled and cache_available and (signal_cache_write_dir != None):
    signal_cache_write = cache.Cache(signal_cache_write_dir, "")
else:
    signal_cache_write = None

classifier_read_enabled = False
if classifier_read_enabled and cache_available and (classifier_cache_read_dir != None):
    classifier_read = cache.Cache(classifier_cache_read_dir, "")
else:
    classifier_read = None

classifier_saving_enabled = True and False
if classifier_saving_enabled and cache_available and (classifier_cache_write_dir != None):
    classifier_write = cache.Cache(classifier_cache_write_dir, "")
else:
    classifier_write = None
    
network_hashes_base_filenames = []
if network_cache_read_dir and network_read:
    network_filenames = cache.find_filenames_beginning_with(network_cache_read_dir, "Network", recursion=False, extension=".pckl")
    for i, network_filename in enumerate(network_filenames):
        network_base_filename = string.split(network_filename, sep=".")[0]
        network_hash = string.split(network_base_filename, sep="_")[-1]
        network_hashes_base_filenames.append((network_base_filename, network_hash))
else:
    network_hashes_base_filenames = []
    
network_hashes_base_filenames.sort(lambda x, y: cmp(x[1], y[1]))

print "%d networks found:"%len(network_hashes_base_filenames)
for i, (network_filename, network_hash) in enumerate(network_hashes_base_filenames):
    print "[%d]"%i, network_filename

network_filename = None
if len(network_hashes_base_filenames) > 0 and (ask_network_loading or load_network_number!=None):
#    flow, layers, benchmark, Network, subimages_train, sl_seq_training = cache.unpickle_from_disk(network_filenames[-1])
    if ask_network_loading or load_network_number==None:
        selected_network = int(raw_input("Please select a network (-1=Train new network):"))
    else:
        print "Network selected from program parameters: ", load_network_number
        selected_network = load_network_number

    if selected_network == -1:
        print "Selected: Train new network"
    else:
        print "Selected: Load Network", selected_network
        network_filename = network_hashes_base_filenames[selected_network][0]

if network_filename != None:
#    network_base_filename = string.split(string.split(network_filename, sep=".")[0], sep="/")[-1]
    network_base_filename = string.split(network_filename, sep=".")[0]
    network_hash = string.split(network_base_filename, sep="_")[-1]

    print "******************************************"
    print "Loading Trained Network and Display Data from Disk         "
    print "******************************************"

    print "network_cach_read_dir", network_cache_read_dir
    print "network_cach_write_dir", network_cache_write_dir
    print "network_filename:", network_filename
    print "network_basefilename:", network_base_filename
    print "network_hash:", network_hash



#        network_write.update_cache([flow, layers, benchmark, Network], None, network_base_dir, "Network"+Network.name+"_ParName"+Parameters.name+"_"+network_hash, overwrite=True, use_hash=network_hash, verbose=True)
#        network_write.update_cache([iSeq, sSeq], None, network_base_dir, "iSeqsSeqData", overwrite=True, use_hash=network_hash, verbose=True)
#        network_write.update_cache(subimages_train, None, network_base_dir, "TrainData", overwrite=True, use_hash=network_hash, verbose=True)
#        network_write.update_cache(sl_seq_training, None, network_base_dir, "SLSeqData", overwrite=True, use_hash=network_hash, verbose=True)
 
#    flow, layers, benchmark, Network = cache.unpickle_from_disk(network_filename)   
    flow, layers, benchmark, Network = network_read.load_obj_from_cache(None, "", network_base_filename, verbose=True)   
    print "Done loading network: " + Network.name
    print flow
#    quit()

    iTrain, sTrain = network_read.load_obj_from_cache(network_hash, network_cache_read_dir, "iTrainsTrainData", verbose=True)   
    print "Done loading iTrain sTrain data: " + sTrain.name

    block_size = sTrain.block_size
    train_mode = iTrain.train_mode
    print "Train mode is:", train_mode

    subimages_train = network_read.load_array_from_cache(network_hash, network_cache_read_dir, "TrainData", verbose=True)   
    print "Done loading subimages_train: ", subimages_train.shape

    sl_seq_training = network_read.load_array_from_cache(network_hash, network_cache_read_dir, "SLSeqData", verbose=True)   
    print "Done loading sl_seq_training: ", sl_seq_training.shape
    
#Why this hash value???? also load whole iSeq, sSeq for first data
#    subimages_train = network_read.load_array_from_cache(hash_value = "1259249913", base_dir = network_base_dir, base_filename="subimages_train_Network", verbose=True)
#    print "Done loading subimages_train: %d Samples"%len(subimages_train)    
    
#    subimages_train_iter = cache.UnpickleLoader2(path=network_base_dir, basefilename="subimages_train_" + network_basefilename, verbose=True)
#   
#    subimages_train = cache.from_iter_to_array(subimages_train_iter, continuous=False, block_size=1, verbose=False)
#    del subimages_train_iter
    
#    sl_seq_training = network_read.load_array_from_cache(hash_value = "1259249913", base_dir = network_base_dir, base_filename="sl_seq_training_Network", verbose=True)
        
#    sl_seq_training_iter = cache.UnpickleLoader2(path=network_base_dir, basefilename="sl_seq_training_" + network_basefilename)
#    sl_seq_training = cache.from_iter_to_array(sl_seq_training_iter, continuous=False, block_size=1, verbose=False)
#    del sl_seq_training_iter

#      
#    subimages_train = load_image_data(seq.input_files, seq.image_width, seq.image_height, seq.subimage_width, \
#                                seq.subimage_height, seq.pixelsampling_x, seq.pixelsampling_y, \
#                                seq.subimage_first_row, seq.subimage_first_column, seq.add_noise_L0, \
#                                seq.convert_format, seq.translations_x, seq.translations_y, seq.trans_sampled, background_type=seq.background_type, color_background_filter=filter, verbose=False)
#    sl_seq_training = flow.execute(subimages_train)

else:
    print "Generating Network..."
#    from hierarchical_networks import linearPCANetworkU11L as Network 
#    from hierarchical_networks import TestNetworkU11L as Network

    #Usually true for voidNetwork1L, but might be also activated for other networks
    use_full_sl_output = False

    #WARNING
    #TODO: Move this to a function
    #Network.patch_network_for_RGB = True and False
    if (sTrain.convert_format == "RGB" or sTrain.convert_format == "HOG02") and Parameters.patch_network_for_RGB:
        if sTrain.convert_format == "RGB":
#            factors = [3, 2, 1.5]
            factors = [2, 1.7, 1.5]
            print "Big Fail!", Network.patch_network_for_RGB
            quit()
        elif sTrain.convert_format == "HOG02":
            factors = [8, 4, 2]
        else:
            er = "unknown conversion factor in network correction for in_channel_dim"
            raise Exception(er)

        for i, layer in enumerate((Network.L0, Network.L1, Network.L2)):
            factor = factors[i]
            if layer != None:
                if layer.pca_out_dim != None and layer.pca_out_dim >= 1:
                    layer.pca_out_dim = int(factor * layer.pca_out_dim)
                if layer.red_out_dim != None and layer.red_out_dim >= 1:
                    layer.red_out_dim = int(factor * layer.red_out_dim)
                #What about ord??? usually it keeps dimension the same, thus it is not specified
                if layer.sfa_out_dim != None and layer.sfa_out_dim >= 1:
                    layer.sfa_out_dim = int(factor * layer.sfa_out_dim)
        print "testing..."
        #quit()



    #Warning
    #WARNING
    #Todo: Correct network creation, to avoid redundant layers (without enough fan in)
    #Todo: Correct update of last PCA Node into Whitening
    #Todo: Move this to a function
    
    skip_layers = 0
    if (hack_image_size == 8) & (enable_hack_image_size == True):
        Network.L3 = None
        Network.L4 = None
        Network.L5 = None
        Network.L6 = None
        Network.L7 = None
        Network.L8 = None
        Network.L9 = None 
        Network.L10 = None
#        Network.layers = [Network.L0, Network.L1, Network.L2, Network.L3, Network.L4]
        skip_layers = 8
        
    if (hack_image_size == 16) & (enable_hack_image_size == True):
        Network.L5 = None
        Network.L6 = None
        Network.L7 = None
        Network.L8 = None
        Network.L9 = None 
        Network.L10 = None
#        Network.layers = [Network.L0, Network.L1, Network.L2, Network.L3, Network.L4]
        skip_layers = 6
        
    if (hack_image_size == 32) & (enable_hack_image_size == True):
        Network.L7 = None #Uncomment for 32x32 Images
        Network.L8 = None
        Network.L9 = None 
        Network.L10 = None
        skip_layers = 4
        
    if (hack_image_size == 64 or hack_image_size == 72 or hack_image_size == 80 or hack_image_size == 95 or hack_image_size == 96) & (enable_hack_image_size == True):      
        Network.L9 = None #Uncomment for 64x64 Images
        Network.L10 = None
        skip_layers = 2
    
    for l in Network.layers:
        print l
    print "SL=", skip_layers
      

    #skip_layers = 0 #TURBOWARNING!!!!
    if skip_layers > 0:
        for i, layer in enumerate(Network.layers):
            if i+skip_layers < len(Network.layers) and layer != None and Network.layers[i+skip_layers] != None:
                if layer.pca_node_class == mdp.nodes.SFANode:
                    print "FIX PCA%d"%i
                    if Network.layers[i+skip_layers].pca_node_class == mdp.nodes.SFANode:
                        if "sfa_expo" in Network.layers[i+skip_layers].pca_args:
                            layer.pca_args["sfa_expo"] = Network.layers[i+skip_layers].pca_args["sfa_expo"]
                        if "pca_expo" in Network.layers[i+skip_layers].pca_args:
                            layer.pca_args["pca_expo"] = Network.layers[i+skip_layers].pca_args["pca_expo"]
                    else:
                        if "sfa_expo" in Network.layers[i+skip_layers].sfa_args:
                            layer.pca_args["sfa_expo"] = Network.layers[i+skip_layers].sfa_args["sfa_expo"]
                        if "pca_expo" in Network.layers[i+skip_layers].sfa_args:
                            layer.pca_args["pca_expo"] = Network.layers[i+skip_layers].sfa_args["pca_expo"]                       
                if layer.ord_node_class == mdp.nodes.SFANode:
                    if "sfa_expo" in Network.layers[i+skip_layers].ord_args:
                        layer.ord_args["sfa_expo"] = Network.layers[i+skip_layers].ord_args["sfa_expo"]
                    if "pca_expo" in Network.layers[i+skip_layers].ord_args:
                        layer.ord_args["pca_expo"] = Network.layers[i+skip_layers].ord_args["pca_expo"]
                if layer.red_node_class == mdp.nodes.SFANode:
                    layer.red_args["sfa_expo"] = Network.layers[i+skip_layers].red_args["sfa_expo"]
                    layer.red_args["pca_expo"] = Network.layers[i+skip_layers].red_args["pca_expo"]
                if layer.sfa_node_class == mdp.nodes.SFANode:
                    print "FixSFA %d"%i
                    if "sfa_expo" in Network.layers[i+skip_layers].sfa_args:
                        layer.sfa_args["sfa_expo"] = Network.layers[i+skip_layers].sfa_args["sfa_expo"]
                    if "pca_expo" in Network.layers[i+skip_layers].sfa_args:
                        layer.sfa_args["pca_expo"] = Network.layers[i+skip_layers].sfa_args["pca_expo"]

    #??? What happened to the other layers???? FIXED!
    Network.layers = []
    for layer in [Network.L0, Network.L1, Network.L2, Network.L3, Network.L4, Network.L5, Network.L6, Network.L7, Network.L8, Network.L9, Network.L10 ]:
        if layer == None:
            break
        else:
            Network.layers.append(layer)

    print "sfa_expo and pca_expo across the network:"
    for i, layer in enumerate(Network.layers):
        if "sfa_expo" in Network.layers[i].pca_args:
            print "pca_args[%d].sfa_expo="%i,  Network.layers[i].pca_args["sfa_expo"]
        if "pca_expo" in Network.layers[i].pca_args:
            print "pca_args[%d].pca_expo="%i,  Network.layers[i].pca_args["pca_expo"]
        if "sfa_expo" in Network.layers[i].sfa_args:
            print "sfa_args[%d].sfa_expo="%i,  Network.layers[i].sfa_args["sfa_expo"]
        if "pca_expo" in Network.layers[i].sfa_args:
            print "sfa_args[%d].pca_expo="%i,  Network.layers[i].sfa_args["pca_expo"]


    if make_last_PCA_node_whithening and (hack_image_size == 16) and (enable_hack_image_size == True) and Network.L4 != None:
        if Network.L4.sfa_node_class == mdp.nodes.PCANode:
            Network.L4.sfa_node_class = mdp.nodes.WhiteningNode
            Network.L4.sfa_out_dim = 50
#            Network.L4.sfa_out_dim = 0
    if make_last_PCA_node_whithening & (hack_image_size == 32) & (enable_hack_image_size == True) and Network.L6 != None:
        if Network.L6.sfa_node_class == mdp.nodes.PCANode:
            Network.L6.sfa_node_class = mdp.nodes.WhiteningNode
            Network.L6.sfa_out_dim = 100
    if make_last_PCA_node_whithening & (hack_image_size == 64 or hack_image_size == 80) & (enable_hack_image_size == True) and Network.L8 != None:
        if Network.L8.sfa_node_class == mdp.nodes.PCANode:
            Network.L8.sfa_node_class = mdp.nodes.WhiteningNode
#            Network.L8.sfa_out_dim = 55
            
#  RTransX  
#    Network.L6.sfa_node_class = mdp.nodes.WhiteningNode
#    Network.L6.sfa_out_dim = 100
#    Network.L8.sfa_node_class = mdp.nodes.WhiteningNode
#    Network.L8.sfa_out_dim = 50
#    Network.L2=None
#    Network.L3=None
#    Network.L4=None
#    Network.L5=None
    #TODO: try loading subimage_data from cache...
    #TODO: Add RGB support
    #TODO: Verify that at least iSeq is the same

    load_subimages_train_signal_from_cache = True
    enable_select_train_signal = True
    
    subimages_train_signal_in_cache = False
    #WARNING: subimage loading disabled until generic training more advanced ... 
    #not clear how to do a clean loading of all datas/display data
    if signal_cache_read and load_subimages_train_signal_from_cache and False:
        print "Looking for subimages_train in cache..."
        
        info_beginning_filename = "subimages_info"  
        subimages_info_filenames = cache.find_filenames_beginning_with(network_cache_read_dir, info_beginning_filename, recursion=False, extension=".pckl")
        print "The following possible training sequences were found:"
        if len(subimages_info_filenames) > 0:
            for i, info_filename in enumerate(subimages_info_filenames):
                info_base_filename = string.split(info_filename, sep=".")[0] #Remove extension          
                (iTrainInfo, sTrainInfo) = subimages_info = signal_cache_read.load_obj_from_cache(base_dir="/", base_filename=info_base_filename, verbose=True)
                print "%d: %s, with %d images of width=%d, height=%d"%(i, iTrainInfo.name, iTrainInfo.num_images, sTrainInfo.subimage_width, sTrainInfo.subimage_height)
                    
            if enable_select_train_signal==True:
                selected_train_sequence = int(raw_input("Please select a training sequence (-1=Reload new data):"))
            else:
                selected_train_sequence = 0
            print "Training sequence %d was selected"%selected_train_sequence

            if selected_train_sequence >= 0:
                info_filename = subimages_info_filenames[selected_train_sequence]
                info_base_filename = string.split(info_filename, sep=".")[0] #Remove extension          
                (iTrain_set, sTrain_set) = signal_cache_read.load_obj_from_cache(base_dir="/", base_filename=info_base_filename, verbose=True)
                
                iTrain = take_0_k_th_from_2D_list(iTrain_set, dataset_for_display_train)
                sTrain = take_0_k_th_from_2D_list(sTrain_set, dataset_for_display_train)

                signal_base_filename = string.replace(info_base_filename, "subimages_info", "subimages_train")
                
                if signal_cache_read.is_splitted_file_in_filesystem(base_dir="/", base_filename=signal_base_filename):
                    print "Subimages train signal found in cache..."
                    subimages_train = signal_cache_read.load_array_from_cache(base_dir="/", base_filename=signal_base_filename, verbose=True)
                    subimages_train_signal_in_cache = True
                    print "Subimages train signal loaded from cache with shape: ",
                    print subimages_train.shape
                    if signal_cache_write:
                        subimages_train_hash = cache.hash_object(subimages_train).hexdigest()
                else:
                    print "Subimages training signal UNEXPECTEDLY NOT FOUND in cache:", signal_base_filename
                    quit()
            
#        subimages_ndim = sTrain.subimage_height * sTrain.subimage_width
#        signal_beginning_filename = "subimages_train_%d"%subimages_ndim
#        subimages_train_filenames = cache.find_filenames_beginning_with(network_base_dir, signal_beginning_filename, recursion=False, extension=".pckl")
#        
#        print "The following possible subimage_train_signals were found:", subimages_train_filenames
#        if len(subimages_train_filenames) > 0:
#            #remove extension .pckl
#            signal_filename = subimages_train_filenames[-1]
#            print "Signal_filename selected:", signal_filename 
#            signal_base_filename = string.split(signal_filename, sep=".")[0]
#            #remove last 6 characters: "_S0000"
#            signal_base_filename = signal_base_filename[0:-6]

    
#Conversion from sSeq to data_sets, param_sets
#Actually train_func_sets
    train_data_sets, train_params_sets = convert_sSeq_to_funcs_params_sets(seq_sets, verbose=False)
    print "now building network"
    train_data_sets, train_params_sets = network_builder.expand_iSeq_sSeq_Layer_to_Network(train_data_sets, train_params_sets, Network)
    print "calling take_first_02D"
    params_node = take_0_k_th_from_2D_list(train_params_sets, k=dataset_for_display_train)

    

    #print "params_node=", params_node
    #quit()
###WARNING!!!!!!!
##block_size = Parameters.block_size
##train_mode = Parameters.train_mode
#print "train_mode=", train_mode
#quit()
# = "mixed", "serial", "complete"
    
    block_size = params_node["block_size"]
    train_mode = params_node["train_mode"]
    
    
    block_size_L0=block_size
    block_size_L1=block_size
    block_size_L2=block_size
    block_size_L3=block_size
    block_size_exec=block_size #(Used only for random walk)

#    if subimages_train_signal_in_cache == False:
#        if seq.input_files == "LoadBinaryData00":
#            subimages_train = load_natural_data(seq.data_base_dir, seq.base_filename, seq.samples, verbose=False)
#        elif seq.input_files == "LoadRawData":
#            subimages_train = load_raw_data(seq.data_base_dir, seq.base_filename, input_dim=seq.input_dim, dtype=seq.dtype, select_samples=seq.samples, verbose=False)
#        else:
#            subimages_train = load_image_data(seq.input_files, seq.image_width, seq.image_height, seq.subimage_width, \
#                                    seq.subimage_height, seq.pixelsampling_x, seq.pixelsampling_y, \
#                                    seq.subimage_first_row, seq.subimage_first_column, seq.add_noise_L0, \
#                                    seq.convert_format, seq.translations_x, seq.translations_y, seq.trans_sampled, background_type=seq.background_type, color_background_filter=filter, verbose=False)

    print "calling take_first_02D again"
    train_func = take_0_k_th_from_2D_list(train_data_sets, k=dataset_for_display_train)
    if coherent_seeds:
        numpy.random.seed(experiment_seed+222222)
    subimages_train = train_func() ### why am I loading the subimages train here???
     
    print "subimages_train[0,0]=%0.40f"%subimages_train[0,0]

    #Avoid double extraction of data from files
    if isinstance(train_data_sets, list) and len(train_data_sets) >=1:
        if isinstance(train_data_sets[0], list) and len(train_data_sets[0]) >=1 and len(train_data_sets[0]) > dataset_for_display_train:
            print "Correcting double loading"
            func = train_data_sets[0][dataset_for_display_train]
            print "substituting func=", func, "for loaded data"
            for i in range(len(train_data_sets)):
                for j in range(len(train_data_sets[i])):
                    print "train_data_sets[%d][%d]="%(i,j), train_data_sets[i][j]
                    if train_data_sets[i][j] is func:
                        print "Correction done"
                        train_data_sets[i][j] = subimages_train

    #TODO: Support train signal chache for generalized training
    if signal_cache_write and subimages_train_signal_in_cache == False and False:
        print "Caching Train Signal..."
        subimages_ndim = subimages_train.shape[1]
        subimages_time = str(int(time.time()))
        iTrain_hash = cache.hash_object(iTrain_sets).hexdigest()
        sTrain_hash = cache.hash_object(sTrain_sets).hexdigest()   
        subimages_base_filename = "subimages_train_%s_%s_%s_%s"%((subimages_ndim, subimages_time, iTrain_hash, sTrain_hash))
        subimages_train_hash = signal_cache_write.update_cache(subimages_train, base_filename=subimages_base_filename, overwrite=True, verbose=True)
        subimages_info = (iTrain, sTrain)
        subimages_info_filename = "subimages_info_%s_%s_%s_%s"%((subimages_ndim, subimages_time, iTrain_hash, sTrain_hash))
        subimages_info_hash = signal_cache_write.update_cache(subimages_info, base_filename=subimages_info_filename, overwrite=True, verbose=True)
        
    t1 = time.time()
    print seq.num_images, "Training Images loaded in %0.3f s"% ((t1-t0))
    #benchmark.append(("Load Info and Training Images", t1-t0))  
 
    save_images_training_base_dir = "/local/tmp/escalafl/Alberto/saved_images_training"
    if save_subimages_training:
        print "saving images to directory:", save_images_training_base_dir
        decimate =  1 # 10
        for i, x in enumerate(subimages_train):
            if i%decimate == 0:
                if seq.convert_format == "L":
                    im_raw = numpy.reshape(x, (seq.subimage_width, seq.subimage_height)) 
                    im = scipy.misc.toimage(im_raw, mode=seq.convert_format)            
                elif seq.convert_format == "RGB":
                    im_raw = numpy.reshape(x, (seq.subimage_width, seq.subimage_height, 3)) 
                    im = scipy.misc.toimage(im_raw, mode=seq.convert_format)
                else:
                    im_raw = numpy.reshape(x, (seq.subimage_width, seq.subimage_height))
                    im = scipy.misc.toimage(im_raw, mode="L")
                
                if save_images_training_supplementary_info == None:
                    filename = "image%05d.png"%(i/decimate)
                    #quit()
                elif save_images_training_supplementary_info == "Class":
                    filename = "image%05d_gt%05d.png"%(i/decimate, iTrain.correct_classes[i])
                elif save_images_training_supplementary_info == "Label":
                    filename = "image%05d_gt%05.5f.png"%(i/decimate, iTrain.correct_labels[i])
                    #quit()
                else:
                    er = "Incorrect value of save_images_training_supplementary_info:"+str(save_images_training_supplementary_info)
                    raise Exception(er)
                fullname = os.path.join(save_images_training_base_dir, filename)
                im.save(fullname)
        #print "done, finishing"
        #quit()


    if save_average_subimage_training:
        average_subimage_training = subimages_train.mean(axis=0)
        if seq.convert_format == "L":
            average_subimage_training = average_subimage_training.reshape(sTrain.subimage_height, sTrain.subimage_width)
        elif seq.convert_format == "RGB":
            average_subimage_training = average_subimage_training.reshape(sTrain.subimage_height, sTrain.subimage_width, 3)
        else:
            average_subimage_training = average_subimage_training.reshape(sTrain.subimage_height, sTrain.subimage_width)
        print "average_subimage_training.shape=", average_subimage_training.shape, "seq.convert_format=", seq.convert_format
        average_subimage_training_I = scipy.misc.toimage(average_subimage_training, mode=seq.convert_format)
        average_subimage_training_I.save("average_image_trainingRGB.jpg", mode=seq.convert_format)
        #print "done, finishing"
        #quit()
        
    print "******************************************"
    print "Creating hierarchy through network_builder"
    print "******************************************"
    #TODO: more primitive but potentially powerful flow especification here should be possible
    flow, layers, benchmark = network_builder.CreateNetwork(Network, sTrain.subimage_width, sTrain.subimage_height, block_size=None, train_mode=None, benchmark=benchmark, in_channel_dim=in_channel_dim)
    
    
    print "Making sure the first switchboard does not add any noise (noise adde during image loading)"
    if isinstance(flow[0], mdp.nodes.PInvSwitchboard):
        flow[0].noise_addition=0.0

    #quit()
    #WARNING
    #flow = mdp.Flow([flow[0]])
    
    #For display purposes we alter here the image shape artificially...
    #TODO: Improve this logic appropiately overall... shape should be really the shape, and in_channel_dim should be used
    print subimage_shape
    if in_channel_dim in [1, 3]:
        subimage_shape = subimage_shape
    else:
        print "Patching subimage_shape for display purposes"
        subimage_shape = (subimage_shape[0], subimage_shape[1]*in_channel_dim) 

#    add_normalization_node = True
    if add_normalization_node:
        normalization_node = mdp.nodes.NormalizeNode()
        flow += normalization_node

    print "flow=", flow
    print len(flow)
    for node in flow:
        print "Node: ", node, "out_dim=", node.output_dim, "input_dim", node.input_dim
    #quit()
    print "*****************************"
    print "Training hierarchy ..."
    print "*****************************"
    

#    enable_parallel = False
#    if enable_parallel == True:
##        flow = mdp.Flow(flow[0:])
#        print "original flow is", flow
#        scheduler = mdp.parallel.ProcessScheduler(n_processes=4)
#        print "***********1"
#        flow = make_flow_parallel(flow)
#        print "parallel flow is", flow
#        print "***********2"

        
    subimages_p = subimages = subimages_train
    #subimages_p = subimages
    #DEFINE TRAINING TYPE. SET ONE OF THE FOLLOWING VARIABLES TO TRUE
    #Either use special (most debugged and efficient) or storage_iterator (saves memory)
    special_training = True
    iterator_training = False
    storage_iterator_training = False    
    
    if special_training is True:
        ttrain0 = time.time()
#Think: maybe training_signal cache can become unnecessary if flow.train is intelligent enough to look for the signal in the cache without loading it???
        if coherent_seeds: #Use same seed as before for data loading... hope the results are the same. Nothing should be done before data generation to ensure this!!!
            numpy.random.seed(experiment_seed+222222) 

        #TODO: f train_data_sets is func() or [[func()]], use instead loaded images!!!!
        sl_seq = sl_seq_training = flow.special_train_cache_scheduler_sets(train_data_sets, params_sets=train_params_sets, verbose=True, benchmark=benchmark, 
                                                                           node_cache_read=node_cache_read, signal_cache_read=signal_cache_read, node_cache_write=node_cache_write, 
                                                                           signal_cache_write=signal_cache_write,scheduler=scheduler,n_parallel=n_parallel,immediate_stop_training=True)
#        sl_seq = sl_seq_training = flow.special_train_cache_scheduler_sets(subimages_p, verbose=True, benchmark=benchmark, node_cache_read=node_cache_read, signal_cache_read=signal_cache_read, node_cache_write=node_cache_write, signal_cache_write=signal_cache_write, scheduler=scheduler, n_parallel=n_parallel)
#        sl_seq = sl_seq_training = flow.special_train_cache_scheduler(subimages_p, verbose=True, benchmark=benchmark, node_cache_read=node_cache_read, signal_cache_read=signal_cache_read, node_cache_write=node_cache_write, signal_cache_write=signal_cache_write, scheduler=scheduler, n_parallel=n_parallel)
        print "sl_seq is", sl_seq
        #quit()
        
        ttrain1 = time.time()
        print "Network trained (specialized way) in time %0.3f s"% ((ttrain1-ttrain0))
        benchmark.append(("Network training  (specialized way)", ttrain1-ttrain0))
    elif iterator_training is True:
        ttrain0 = time.time()
    #WARNING, introduce smart way of computing chunk_sizes
        input_iter = cache.chunk_iterator(subimages_p, 4, block_size, continuous=False)
        
    #    sl_seq = sl_seq_training = flow.iterator_train(input_iter)
        flow.iterator_train(input_iter, block_size, continuous=True)
        sl_seq = sl_seq_training = flow.execute(subimages_p)
        
        ttrain1 = time.time()
        print "Network trained (iterator way) in time %0.3f s"% ((ttrain1-ttrain0))
        benchmark.append(("Network training (iterator way)", ttrain1-ttrain0))
    elif storage_iterator_training is True:
        ttrain0 = time.time()
    #Warning: introduce smart way of computing chunk_sizes
    #    input_iter = chunk_iterator(subimages_p, 15 * 15 / block_size, block_size, continuous=False)
        input_iter = cache.chunk_iterator(subimages_p, 4, block_size, continuous=False)
        
    #    sl_seq = sl_seq_training = flow.iterator_train(input_iter)
    #WARNING, continuous should not always be true
        flow.storage_iterator_train(input_iter, "/local/tmp/escalafl/simulations/gender", "trainseq", block_size, continuous=True)
    
        output_iterator = cache.UnpickleLoader2(path="/local/tmp/escalafl/simulations/gender", \
                                          basefilename="trainseq"+"_N%03d"%(len(flow)-1))
            
        sl_seq = sl_seq_training = cache.from_iter_to_array(output_iterator, continuous=False, block_size=block_size, verbose=0)
        del output_iterator
        
        ttrain1 = time.time()
        print "Network trained (storage iterator way) in time %0.3f s"% ((ttrain1-ttrain0))
        benchmark.append(("Network training (storage iterator way)", ttrain1-ttrain0))
    else:
        ttrain0 = time.time()
        flow.train(subimages_p)
        y = flow.execute(subimages_p[0:1]) #stop training
        sl_seq = sl_seq_training = flow.execute(subimages_p)
        ttrain1 = time.time()
        print "Network trained (MDP way) in time %0.3f s"% ((ttrain1-ttrain0))
        benchmark.append(("Network training (MDP way)", ttrain1-ttrain0))
    
    nodes_in_flow = len(flow)
    last_sfa_node = flow[nodes_in_flow-1]
    if isinstance(last_sfa_node, mdp.hinet.CloneLayer) or \
    isinstance(last_sfa_node, mdp.hinet.Layer):
        last_sfa_node = last_sfa_node.nodes[0]

    if isinstance(last_sfa_node, mdp.nodes.SFANode):
        if iTrain.correct_labels[0:10].sum() <= 0:
            start_negative = True
        else:
            start_negative = False
        sl_seq = sl_seq_training = more_nodes.sfa_pretty_coefficients(last_sfa_node, sl_seq_training, start_negative=start_negative) #default start_negative=True #WARNING!
    else:
        print "SFA coefficients not made pretty, last node was not SFA!!!"


    print "Since training is finished, making sure the switchboards do not add any noise from now on"
    for node in flow:
        if isinstance(node, mdp.nodes.PInvSwitchboard):
            node.noise_addition=0.0

#    For display purposes ignore output of training, and concentrate on display signal:
    sl_seq = sl_seq_training = flow.execute(subimages_train)
    if feature_cut_off_level > 0.0:
        sl_seq = sl_seq_training = cutoff(sl_seq_training, min_cutoff , max_cutoff)
    
#    try:
#        cache.pickle_to_disk([flow, layers, benchmark, Network, subimages_train, sl_seq_training], os.path.join(network_base_dir, "Network_" + str(int(time.time()))+ ".pckl"))
#   hashing Network info and training data would make more sense here...
    network_hash = str(int(time.time()))
#    network_filename = "Network_" + network_hash + ".pckl"

    if network_write:
        print "Saving flow, layers, benchmark, Network ..."
        #update cache is not adding the hash to the filename,so we add it manually
        network_write.update_cache(flow, None, network_cache_write_dir, "JustFlow"+sTrain.name+"_"+network_hash, overwrite=True, use_hash=network_hash, verbose=True)
        network_write.update_cache(layers, None, network_cache_write_dir, "JustLayers"+sTrain.name+"_"+network_hash, overwrite=True, use_hash=network_hash, verbose=True)
        network_write.update_cache(benchmark, None, network_cache_write_dir, "JustBenchmark"+sTrain.name+"_"+network_hash, overwrite=True, use_hash=network_hash, verbose=True)
        network_write.update_cache(Network, None, network_cache_write_dir, "JustNetwork"+sTrain.name+"_"+network_hash, overwrite=True, use_hash=network_hash, verbose=True)

        network_write.update_cache([flow, layers, benchmark, Network], None, network_cache_write_dir, "Network"+Network.name+"_ParName"+Parameters.name+"_"+network_hash, overwrite=True, use_hash=network_hash, verbose=True)
        network_write.update_cache([iTrain, sTrain], None, network_cache_write_dir, "iTrainsTrainData"+"_"+network_hash, overwrite=True, use_hash=network_hash, verbose=True)
        network_write.update_cache(subimages_train, None, network_cache_write_dir, "TrainData"+"_"+network_hash, overwrite=True, use_hash=network_hash, verbose=True)
        network_write.update_cache(sl_seq_training, None, network_cache_write_dir, "SLSeqData"+"_"+network_hash, overwrite=True, use_hash=network_hash, verbose=True)
        #obj, obj_data=None, base_dir = None, base_filename=None, overwrite=True, use_hash=None, verbose=True

    if signal_cache_write:
        print "Caching sl_seq_training  Signal... (however, it's never read!)"
        signal_ndim = sl_seq_training.shape[1]
        signal_time = str(int(time.time()))
        flow_hash = cache.hash_object(flow).hexdigest()
        #TODO: Add subimages_train_hash to signal filename. Compute according to first data/parameter sets
        signal_base_filename = "sfa_signal_ndim%s_time%s_flow%s"%((signal_ndim, signal_time, flow_hash))
        signal_cache_write.update_cache(sl_seq_training, base_filename=signal_base_filename, overwrite=True, verbose=True)
    

#    cache.pickle_to_disk([flow, layers, benchmark, Network], os.path.join(network_base_dir, network_filename ))
#    print "2"
#    subimages_train_iter = chunk_iterator(subimages_train, chunk_size=5000, block_size=1, continuous=False, verbose=True)
#    print "3"
#    cache.save_iterable2(subimages_train_iter, path=network_base_dir, basefilename="subimages_train_" + network_filename)   
#    print "4"
#    del subimages_train_iter
#    print "5"
#    sl_seq_training_iter = chunk_iterator(sl_seq_training, chunk_size=200000, block_size=1, continuous=False, verbose=True)
#    print "6"
#    cache.save_iterable2(sl_seq_training_iter, path=network_base_dir, basefilename="sl_seq_training_" + network_filename)
#    print "7"
#    del sl_seq_training_iter
#    print "8"
    print "Saving Finished"
#    except:
#        print "Saving Failed, reason:", ex


print "taking into account objective_label=%d"%objective_label
if len(iTrain.correct_labels.shape)==2:
    print "correction..."
    iTrain.correct_labels = iTrain.correct_labels[:,objective_label].flatten()
    Parameters.iSeenid.correct_labels = Parameters.iSeenid.correct_labels[:,objective_label].flatten()
    Parameters.iNewid[0][0].correct_labels = Parameters.iNewid[0][0].correct_labels[:,objective_label].flatten()
        
    iTrain.correct_classes = iTrain.correct_classes[:,objective_label].flatten()
    Parameters.iSeenid.correct_classes = Parameters.iSeenid.correct_classes[:,objective_label].flatten()
    Parameters.iNewid[0][0].correct_classes = Parameters.iNewid[0][0].correct_classes[:,objective_label].flatten()
print "iTrain.correct_classes=", iTrain.correct_classes
print "Parameters.iSeenid.correct_classes=", Parameters.iSeenid.correct_classes
print "done"


# print "taking into account objective_label=%d"%objective_label
# if isinstance(iTrain_set, list):
#     iTrain0 = iTrain_set[len(iTrain_set)-1][0]
# else:
#     iTrain0 = take_0_k_th_from_2D_list(iTrain_set, k=0)
# 
# if len(iTrain0.correct_labels.shape)==2:
#     print "correction..."
#     iTrain0.correct_labels = iTrain0.correct_labels[:,objective_label].flatten()
#     Parameters.iSeenid.correct_labels = Parameters.iSeenid.correct_labels[:,objective_label].flatten()
#     Parameters.iNewid[0][0].correct_labels = Parameters.iNewid[0][0].correct_labels[:,objective_label].flatten()
#         
#     iTrain0.correct_classes = iTrain0.correct_classes[:,objective_label].flatten()
#     Parameters.iSeenid.correct_classes = Parameters.iSeenid.correct_classes[:,objective_label].flatten()
#     Parameters.iNewid[0][0].correct_classes = Parameters.iNewid[0][0].correct_classes[:,objective_label].flatten()
# print "iTrain0.correct_classes=", iTrain0.correct_classes
# print "Parameters.iSeenid.correct_classes=", Parameters.iSeenid.correct_classes
# print "done"



if coherent_seeds:
    numpy.random.seed(experiment_seed+333333)


#Improve this!
#Fixing some unassigned variables
subimages_p = subimages = subimages_train
sl_seq_training = sl_seq_training[:,skip_num_signals:]
sl_seq = sl_seq_training


print "subimages_train[0,0]=%0.40f"%subimages_train[0,0]

print "Done creating / training / loading network"   
y = flow.execute(subimages_p[0:1])
print y.shape
more_nodes.describe_flow(flow)
more_nodes.display_eigenvalues(flow, mode="Average") #"FirstNodeInLayer", "Average", "All"

hierarchy_out_dim = y.shape[1]-skip_num_signals

print "hierarchy_out_dim (real output data) =", hierarchy_out_dim
print "last_node_out_dim=", flow[-1].output_dim
if isinstance(flow[-1], (mdp.hinet.Layer, mdp.hinet.CloneLayer)):
    print "last_Layer_node_out_dim=", flow[-1][0].output_dim
    print "last node of network is a layer! is this a mistake?"
    #quit()
if hierarchy_out_dim != flow[-1].output_dim:
    print "error!!! hierarchy_out_dim != flow[-1].output_dim"
    print "Perhaps enable_reduced_image_sizes=True or enable_hack_image_size=True for linear network?"
    quit()
    
results = SystemParameters.ExperimentResult()
results.name = Parameters.name
results.network_name = Network.name
results.layers_name = []
for lay in layers:
    results.layers_name.append(lay.name)
results.iTrain = iTrain
results.sTrain = sTrain
results.iSeenid = iSeenid
results.sSeenid = sSeenid
results.iNewid = iNewid
results.sNewid = sNewid


print "Computing typical delta, eta values for Train SFA Signal"
t_delta_eta0 = time.time()
results.typical_delta_train, results.typical_eta_train = sfa_libs.comp_typical_delta_eta(sl_seq_training, block_size, num_reps=200, training_mode=iTrain.train_mode)
results.brute_delta_train = sfa_libs.comp_delta_normalized(sl_seq_training)
results.brute_eta_train = sfa_libs.comp_eta(sl_seq_training)
t_delta_eta1 = time.time()
print "typical_delta_train=", results.typical_delta_train
print "typical_delta_train[0:31].sum()=", results.typical_delta_train[0:31].sum()
#print "typical_eta_train=", results.typical_eta_train
#print "brute_delta_train=", results.brute_delta_train
#print "brute_eta_train=", results.brute_eta_train

print "computed delta/eta in %0.3f ms"% ((t_delta_eta1-t_delta_eta0)*1000.0)
benchmark.append(("Computation of delta, eta values for Train SFA Signal", t_delta_eta1-t_delta_eta0))


print "Setting correct classes and labels for the Classifier/Regression, Train SFA Signal"
correct_classes_training = iTrain.correct_classes
print "correct_classes_training=", correct_classes_training
correct_labels_training = iTrain.correct_labels

if convert_labels_days_to_years:
    correct_labels_training = correct_labels_training / DAYS_IN_A_YEAR
    if integer_label_estimation:
        correct_labels_training = (correct_labels_training+0.0006).astype(int)

#     print "WARNING, ADDING A BIAS OF -0.5 TO ESTIMATION OF NEWID ONLY!!!"
#     regression_Gauss_newid += -0.5
#     regressionMAE_Gauss_newid += -0.5
    
#print "Testing for bug in first node..."
#print "subimages_train[0:1, 0:10]="
#print subimages_train[0:1, 0:10]
#print "flow[0].execute(subimages_train[0:1])[:,0:10]="
#print flow[0].execute(subimages_train[0:1])[:, 0:10]



print "Loading test images, seen ids..."
t_load_images0 = time.time()
#im_seq_base_dir = "/local/tmp/escalafl/Alberto/testing_seenid"
#im_seq_base_dir = "/local/tmp/escalafl/Alberto/training"

#FOR LEARNING IDENTITIES, INVARIANT TO VERTICAL ANGLE AND TRANSLATIONS
#im_seq_base_dir = "/local/tmp/escalafl/Alberto/Renderings20x500"
#ids=range(0,4)
#expressions=[0]
#morphs=[0]
#poses=range(0,500)
#lightings=[0]
##slow_signal=0
#step=4
#offset=1
#image_files_seenid = create_image_filenames(im_seq_base_dir, slow_signal, ids, expressions, morphs, poses, lightings, step, offset)

print "LOADING KNOWNID TEST INFORMATION"      
image_files_seenid = iSeenid.input_files
num_images_seenid = iSeenid.num_images
block_size_seenid = iSeenid.block_size
seq = sSeenid

if coherent_seeds:
    numpy.random.seed(experiment_seed+444444)

if seq.input_files == "LoadBinaryData00":
    subimages_seenid = load_natural_data(seq.data_base_dir, seq.base_filename, seq.samples, verbose=False)
elif seq.input_files == "LoadRawData":
    subimages_seenid = load_raw_data(seq.data_base_dir, seq.base_filename, input_dim=seq.input_dim, dtype=seq.dtype, select_samples=seq.samples, verbose=False)
else:
#W
#    subimages_seenid = experiment_datasets.load_data_from_sSeq(seq)
    subimages_seenid = seq.load_data(seq)

#    subimages_seenid = load_image_data(seq.input_files, seq.image_width, seq.image_height, seq.subimage_width, \
#                            seq.subimage_height, seq.pixelsampling_x, seq.pixelsampling_y, \
#                            seq.subimage_first_row, seq.subimage_first_column, seq.add_noise_L0, \
#                            seq.convert_format, seq.translations_x, seq.translations_y, seq.trans_sampled, background_type=seq.background_type, color_background_filter=filter, verbose=False)

t_load_images1 = time.time()

#average_subimage_seenid = subimages_seenid.sum(axis=0)*1.0 / num_images_seenid
#average_subimage_seenid_I = scipy.cache.toimage(average_subimage_seenid.reshape(sSeenid.subimage_height, sSeenid.subimage_width, 3), mode="RGB")
#average_subimage_seenid_I.save("average_image_seenidRGB2.jpg", mode="RGB")

print num_images_seenid, " Images loaded in %0.3f s"% ((t_load_images1-t_load_images0))

t_exec0 = time.time()
print "Execution over known id testing set..."
print "Input Signal: Known Id test images"
sl_seq_seenid = flow.execute(subimages_seenid)
sl_seq_seenid = sl_seq_seenid[:,skip_num_signals:]

if feature_cut_off_level > 0.0:  
    print "before cutoff sl_seq_seenid= ", sl_seq_seenid
    sl_seq_seenid = cutoff(sl_seq_seenid, min_cutoff, max_cutoff)

sl_seq_training_min = sl_seq_training.min(axis=0)
sl_seq_training_max = sl_seq_training.max(axis=0)


if clip_seenid_newid_to_training:
    print "clipping sl_seq_seenid"
    sl_seq_seenid_min = sl_seq_seenid.min(axis=0)
    sl_seq_seenid_max = sl_seq_seenid.max(axis=0)
    print "sl_seq_training_min=", sl_seq_training_min
    print "sl_seq_training_max=", sl_seq_training_max   
    print "sl_seq_seenid_min=", sl_seq_seenid_min
    print "sl_seq_seenid_max=", sl_seq_seenid_max
    sl_seq_seenid = numpy.clip(sl_seq_seenid, sl_seq_training_min, sl_seq_training_max)
    
    
if add_noise_to_seenid:#Using uniform noise for speed over normal noise
    noise_amplitude = (3**0.5)*0.5 #standard deviation 0.00005
    print "adding noise to sl_seq_seenid, with noise_amplitude:", noise_amplitude
    sl_seq_seenid += noise_amplitude * numpy.random.uniform(-1.0, 1.0, size=sl_seq_seenid.shape) 



t_exec1 = time.time()
print "Execution over Known Id in %0.3f s"% ((t_exec1 - t_exec0))


print "Computing typical delta, eta values for Seen Id SFA Signal"
t_delta_eta0 = time.time()
results.typical_delta_seenid, results.typical_eta_seenid = sfa_libs.comp_typical_delta_eta(sl_seq_seenid, iSeenid.block_size, num_reps=200, training_mode=iSeenid.train_mode)
print "sl_seq_seenid=", sl_seq_seenid
results.brute_delta_seenid = sfa_libs.comp_delta_normalized(sl_seq_seenid)
results.brute_eta_seenid= sfa_libs.comp_eta(sl_seq_seenid)
t_delta_eta1 = time.time()
print "typical_delta_seenid=", results.typical_delta_seenid
print "typical_delta_seenid[0:31].sum()=", results.typical_delta_seenid[0:31].sum()
print "typical_eta_seenid=", results.typical_eta_seenid
print "brute_delta_seenid=", results.brute_delta_seenid
#print "brute_eta_seenid=", results.brute_eta_seenid
print "computed delta/eta in %0.3f ms"% ((t_delta_eta1-t_delta_eta0)*1000.0)


print "Setting correct labels/classes data for seenid"
correct_classes_seenid = iSeenid.correct_classes
correct_labels_seenid = iSeenid.correct_labels
correct_labels_seenid_real = correct_labels_seenid.copy()

if convert_labels_days_to_years:
    correct_labels_seenid_real = correct_labels_seenid_real / DAYS_IN_A_YEAR
    correct_labels_seenid /= DAYS_IN_A_YEAR
    if integer_label_estimation:
        correct_labels_seenid = (correct_labels_seenid+0.0006).astype(int)


t8 = time.time()
t_classifier_train0 = time.time()
print "*** Training Classifier/Regression"

#W
if use_full_sl_output == True or reg_num_signals == 0:
    results.reg_num_signals = reg_num_signals = sl_seq_training.shape[1]
#else:
#    results.reg_num_signals = reg_num_signals = 3  #42



#WARNIGN!!! USING NEWID INSTEAD OF TRAINING
#cf_sl = sl_seq_training
#cf_num_samples = cf_sl.shape[0]
#cf_correct_labels = correct_labels_training
#cf_correct_classes = iTrain.correct_classes
#cf_spacing = cf_block_size = iTrain.block_size

cf_sl = sl_seq_seenid
cf_num_samples = cf_sl.shape[0]
cf_correct_labels = correct_labels_seenid_real
cf_correct_classes = iSeenid.correct_classes
cf_spacing = cf_block_size = iSeenid.block_size

#if "correct_classes_from_zero" in sSeenid:
#    all_classes = sSeenid.correct_classes_from_zero
#else:
all_classes = numpy.unique(cf_correct_classes)

#if "avg_labels" in sSeenid:
#    avg_labels = sSeenid.avg_labels
#else:
avg_labels = more_nodes.compute_average_labels_for_each_class(cf_correct_classes, cf_correct_labels)

#correct_labels_training = numpy.arange(len(labels_ccc_training))
#labels_classif = wider_1Darray(numpy.arange(iTrain.MIN_GENDER, iTrain.MAX_GENDER, iTrain.GENDER_STEP), iTrain.block_size)
#correct_labels_training = labels_classif
#print "labels_classif.shape = ", labels_classif.shape, " blocksize= ", block_size
#correct_classes_training = numpy.arange(len(labels_classif)) / block_size

if reg_num_signals <= 128 and (Parameters.analysis != False) and enable_NCC:
    enable_ncc_cfr = True
else:
    enable_ncc_cfr = False

if reg_num_signals <= 128 and (Parameters.analysis != False) and enable_GC:
    enable_ccc_Gauss_cfr = True
    enable_gc_cfr = True
else:
    enable_ccc_Gauss_cfr = False
    enable_gc_cfr = False
    
if reg_num_signals <= 64 and (Parameters.analysis != False) and enable_kNN:
    enable_kNN_cfr = True
else:
    enable_kNN_cfr = False
    
if reg_num_signals <= 120 and (Parameters.analysis != False) and enable_svm: # and False:
    enable_svm_cfr = True
else:
    enable_svm_cfr = False
    
if reg_num_signals <= 8192 and (Parameters.analysis != False) and enable_lr:
    enable_lr_cfr = True
else:
    enable_lr_cfr = False

#WARNING!!!!
#enable_svm_cfr = False
#enable_lr_cfr = False
#TODO: Correct S2SC, it should accept a correct_classes parameter

if enable_ncc_cfr == True:
    print "Training Classifier/Regression NCC"
    ncc_node = mdp.nodes.NearestMeanClassifier()
    ncc_node.train(x=cf_sl[:,0:reg_num_signals], labels = cf_correct_classes)
    ncc_node.stop_training()

if enable_ccc_Gauss_cfr == True:
    print "Training Classifier/Regression GC..."
#    S2SC = classifiers.Simple_2_Stage_Classifier()
#    S2SC.train(data=cf_sl[:,0:reg_num_signals], labels=cf_correct_labels, classes= cf_correct_classes, block_size=cf_block_size,spacing=cf_block_size)
    print "unique labels =", numpy.unique(cf_correct_classes)
    print "len(unique_labels)=", len(numpy.unique(cf_correct_classes))
    print "cf_sl[0,:]=", cf_sl[0,:]
    print "cf_sl[1,:]=", cf_sl[1,:]
    print "cf_sl[2,:]=", cf_sl[2,:]
    print "cf_sl[3,:]=", cf_sl[3,:]
    print "cf_sl[4,:]=", cf_sl[4,:]
    print "cf_sl[5,:]=", cf_sl[5,:]

#    for c in numpy.unique(cf_correct_classes):
#        print "class %f appears %d times"%(c, (cf_correct_classes==c).sum())
#        print "mean(cf_sl[c=%d,:])="%c, cf_sl[cf_correct_classes==c, :].mean(axis=0)
#        print "std(cf_sl[c=%d,:])="%c, cf_sl[cf_correct_classes==c, :].std(axis=0)


    GC_node = mdp.nodes.GaussianClassifier()
    GC_node.train(x=cf_sl[:,0:reg_num_signals], labels = cf_correct_classes) #Functions for regression use class values!!!
    GC_node.stop_training()
    
    t_classifier_train1 = time.time()
    benchmark.append(("Training Classifier/Regression GC", t_classifier_train1-t_classifier_train0))

t_classifier_train1 = time.time()

if enable_kNN_cfr == True:
    print "Training Classifier/Regression kNN, for k=%d..."%kNN_k
    kNN_node = mdp.nodes.KNNClassifier(k=kNN_k)
    kNN_node.train(x=cf_sl[:,0:reg_num_signals], labels = cf_correct_classes)
    kNN_node.stop_training()
    
    t_classifier_train1b = time.time()
    benchmark.append(("Training Classifier/Regression kNN", t_classifier_train1b-t_classifier_train1))

t_classifier_train1 = time.time()


def my_sigmoid(x):
    return numpy.tanh(5*x)

if cf_block_size != None:
    if isinstance(cf_block_size, (numpy.float, numpy.float64, numpy.int)):
        num_blocks = cf_sl.shape[0]/cf_block_size
    else:
        num_blocks = len(cf_block_size)
else:
    num_blocks = cf_sl.shape[0]

def svm_compute_range(data):
    mins = data.min(axis=0)
    maxs = data.max(axis=0)
    return mins, maxs

def svm_scale(data, mins, maxs, svm_min, svm_max):
    return (data - mins)*(svm_max-svm_min) / (maxs-mins) + svm_min

if enable_svm_cfr == True:
    print "Training SVM..."
    # params names: ["svm_type", "kernel_type", "degree", "gamma", "coef0", "cache_size", 
    #                  "eps", "C", "nr_weight", "weight_label", "weight", "nu", "p", "shrinking", "probability"]
    #kernels = ["RBF", "LINEAR", "POLY", "SIGMOID"]
    #classifiers = ["C_SVC", "NU_SVC", "ONE_CLASS", "EPSILON_SVR", "NU_SVR"]
    
    params = {"C":svm_C, "gamma":svm_gamma, "nu":0.6, "eps":0.0001}
    svm_node = mdp.nodes.LibSVMClassifier(kernel="RBF", classifier="C_SVC", params=params, probability=True)
    data_mins, data_maxs = svm_compute_range(cf_sl[:,0:reg_num_signals])
    svm_node.train(svm_scale(cf_sl[:,0:reg_num_signals], data_mins, data_maxs, svm_min, svm_max), cf_correct_classes)
    if svm_gamma==0:
        svm_gamma = 1.0 / (num_blocks)
    svm_node.stop_training()
#    svm_node.stop_training(svm_type=libsvm.C_SVC, kernel_type=libsvm.RBF, C=svm_C, gamma=svm_gamma, nu=0.6, eps=0.0001, expo=1.6)

#HACK
#svm_node = classifiers.ClosestDistanceClassifierNew()
#svm_node.train(cf_sl[:,0:reg_num_signals], cf_correct_labels)

#    svm_node.train_probability(cf_sl[:,0:reg_num_signals], cf_block_size, activation_func = my_sigmoid)

#    svm_node.eban_probability(cf_sl[:,0:reg_num_signals])
#    quit()

if enable_lr_cfr == True:
    print "Training LR..."
    lr_node = mdp.nodes.LinearRegressionNode(with_bias=True, use_pinv=False)
    lr_node.train(cf_sl[:,0:reg_num_signals], cf_correct_labels.reshape((cf_sl.shape[0], 1)))
    lr_node.stop_training()


if classifier_write and enable_ccc_Gauss_cfr:
    print "Saving Gaussian Classifier"
    cf_sl_hash = cache.hash_array(cf_sl).hexdigest() 
    #update cache is not adding the hash to the filename,so we add it manually
    classifier_filename = "GaussianClassifier_NetName"+Network.name+"_ParName"+Parameters.name+"_NetH" + network_hash + "_CFSlowH"+ cf_sl_hash +"_NumSig%03d"%reg_num_signals
    classifier_write.update_cache(GC_node, None, None, classifier_filename, overwrite=True, verbose=True)
#****************************************************************
####TODO: make classifier cash work!
####TODO: review eban_svm model & implementation! beat normal svm!

print "Executing/Executed over training set..."
print "Input Signal: Training Data"
subimages_training = subimages
num_images_training = num_images

print "Classification/Regression over training set..."
t_class0 = time.time()

if enable_ncc_cfr == True:
    print "ncc classify..."
    classes_ncc_training = numpy.array(ncc_node.label(sl_seq_training[:,0:reg_num_signals]))
    labels_ncc_training = more_nodes.map_class_numbers_to_avg_label(all_classes, avg_labels, classes_ncc_training)
    print classes_ncc_training
else:
    classes_ncc_training = labels_ncc_training = numpy.zeros(num_images_training)

if enable_ccc_Gauss_cfr == True:
    print "GC classify..."
#    classes_ccc_training, labels_ccc_training = S2SC.classifyCDC(sl_seq_training[:,0:reg_num_signals])
#    classes_Gauss_training, labels_Gauss_training = S2SC.classifyGaussian(sl_seq_training[:,0:reg_num_signals])
#    regression_Gauss_training = S2SC.GaussianRegression(sl_seq_training[:,0:reg_num_signals])
#    probs_training = S2SC.GC_L0.class_probabilities(sl_seq_training[:,0:reg_num_signals])
    classes_Gauss_training = numpy.array(GC_node.label(sl_seq_training[:,0:reg_num_signals]))
    labels_Gauss_training = more_nodes.map_class_numbers_to_avg_label(all_classes, avg_labels, classes_Gauss_training)
    
    regression_Gauss_training = GC_node.regression(sl_seq_training[:,0:reg_num_signals], avg_labels)
    regressionMAE_Gauss_training = GC_node.regressionMAE(sl_seq_training[:,0:reg_num_signals], avg_labels)
    probs_training = GC_node.class_probabilities(sl_seq_training[:,0:reg_num_signals])
    
    softCR_Gauss_training = GC_node.softCR(sl_seq_training[:,0:reg_num_signals], correct_classes_training)
else:
    classes_Gauss_training =  labels_Gauss_training = regression_Gauss_training = regressionMAE_Gauss_training = numpy.zeros(num_images_training) 
    probs_training = numpy.zeros((num_images_training, 2))
    softCR_Gauss_training = 0.0

if enable_kNN_cfr == True:
    print "kNN classify... (k=%d)"%kNN_k
    classes_kNN_training = numpy.array(kNN_node.label(sl_seq_training[:,0:reg_num_signals]))
    labels_kNN_training = more_nodes.map_class_numbers_to_avg_label(all_classes, avg_labels, classes_kNN_training) 
else:
    classes_kNN_training = labels_kNN_training = numpy.zeros(num_images_training) 

skip_svm_training = False

if enable_svm_cfr == True and skip_svm_training==False:
    print "SVM classify..."
    classes_svm_training= svm_node.label(svm_scale(sl_seq_training[:,0:reg_num_signals], data_mins, data_maxs, svm_min, svm_max))
#    regression_svm_training= svm_node.label_of_class(classes_svm_training)
#    regression2_svm_training= svm_node.regression(sl_seq_training[:,0:reg_num_signals])
#    regression3_svm_training= regression2_svm_training
    regression_svm_training= more_nodes.map_class_numbers_to_avg_label(all_classes, avg_labels, classes_svm_training)
    regression2_svm_training= more_nodes.map_class_numbers_to_avg_label(all_classes, avg_labels, classes_svm_training)
    regression3_svm_training= more_nodes.map_class_numbers_to_avg_label(all_classes, avg_labels, classes_svm_training)
#    regression3_svm_training= svm_node.eban_regression(sl_seq_training[:,0:reg_num_signals])
    #Warning!!!
#    raw_input("please enter something to continue")
        
#    eban_probs = svm_node.eban_probability2(sl_seq_training[0:2,0:reg_num_signals])
#    print "len(eban_probs[0])= ", len(eban_probs[0])
#    print eban_probs
#
#    
#    eban_probs = svm_node.eban_probability(sl_seq_training[num_images_training/2:num_images_training/2+2,0:reg_num_signals])
#    print "len(eban_probs[0])= ", len(eban_probs[0])
#    print eban_probs
#
#    eban_probs = svm_node.eban_probability(sl_seq_training[-2:,0:reg_num_signals])
#    print "len(eban_probs[0])= ", len(eban_probs[0])
#    print eban_probs
#
#    quit()
else:
    classes_svm_training=regression_svm_training = regression2_svm_training = regression3_svm_training=numpy.zeros(num_images_training)

#HACK
#classes_svm_training= svm_node.classifyNoMem(sl_seq_training[:,0:reg_num_signals])

if enable_lr_cfr == True:
    print "LR execute..."
    regression_lr_training = lr_node.execute(sl_seq_training[:,0:reg_num_signals]).flatten()
else:
    regression_lr_training = numpy.zeros(num_images_training)


if output_instead_of_SVM2:
    regression2_svm_training = (sl_seq_training[:,0] * orig_train_label_std) + orig_train_label_mean
    print "Applying cutoff to the label estimations for LR and Linear Scaling (SVM2)"
    regression2_svm_training = cutoff(regression2_svm_training, orig_train_label_min, orig_train_label_max)
    regression_lr_training = cutoff(regression_lr_training, orig_train_label_min, orig_train_label_max)

print "Classification of training data: ", labels_kNN_training
t_classifier_train2 = time.time()

print "Classifier trained in time %0.3f s"% ((t_classifier_train1 - t_classifier_train0))
print "Training Images Classified in time %0.3f s"% ((t_classifier_train2 - t_classifier_train1))
benchmark.append(("Classification of Training Images", t_classifier_train2-t_classifier_train1))

t_class1 = time.time()
print "Classification/Regression over Training Set in %0.3f s"% ((t_class1 - t_class0))

if integer_label_estimation:
    print "Making all label estimations for training data integer numbers"
    if convert_labels_days_to_years:
        labels_ncc_training = labels_ncc_training.astype(int)
        regression_Gauss_training = regression_Gauss_training.astype(int)
        regressionMAE_Gauss_training = regressionMAE_Gauss_training.astype(int)
        labels_kNN_training = labels_kNN_training.astype(int)
        regression_svm_training = regression_svm_training.astype(int)
        regression2_svm_training = regression2_svm_training.astype(int)
        regression3_svm_training = regression3_svm_training.astype(int)
        regression_lr_training = regression_lr_training.astype(int)   
    else:
        labels_ncc_training = numpy.rint(labels_ncc_training)
        regression_Gauss_training = numpy.rint(regression_Gauss_training)
        regressionMAE_Gauss_training = numpy.rint(regressionMAE_Gauss_training)
        labels_kNN_training = numpy.rint(labels_kNN_training)
        regression_svm_training = numpy.rint(regression_svm_training)
        regression2_svm_training = numpy.rint(regression2_svm_training)
        regression3_svm_training = numpy.rint(regression3_svm_training)
        regression_lr_training = numpy.rint(regression_lr_training)   
    print "regressionMAE_Gauss_training[0:5]=", regressionMAE_Gauss_training[0:5]
    

t_class0 = time.time()
if enable_ncc_cfr == True:
    print "NCC classify..."
    classes_ncc_seenid = numpy.array(ncc_node.label(sl_seq_seenid[:,0:reg_num_signals]))
    labels_ncc_seenid = more_nodes.map_class_numbers_to_avg_label(all_classes, avg_labels, classes_ncc_seenid)
    print classes_ncc_seenid
else:
    classes_ncc_seenid = labels_ncc_seenid = numpy.zeros(num_images_seenid) 

if enable_ccc_Gauss_cfr == True:
#    classes_ccc_seenid, labels_ccc_seenid = S2SC.classifyCDC(sl_seq_seenid[:,0:reg_num_signals])
#    classes_Gauss_seenid, labels_Gauss_seenid = S2SC.classifyGaussian(sl_seq_seenid[:,0:reg_num_signals])
#    print "Classification of Seen id test images: ", labels_ccc_seenid
#    regression_Gauss_seenid = S2SC.GaussianRegression(sl_seq_seenid[:,0:reg_num_signals])
#    probs_seenid = S2SC.GC_L0.class_probabilities(sl_seq_seenid[:,0:reg_num_signals])
    
    classes_Gauss_seenid = numpy.array(GC_node.label(sl_seq_seenid[:,0:reg_num_signals]))
    labels_Gauss_seenid = more_nodes.map_class_numbers_to_avg_label(all_classes, avg_labels, classes_Gauss_seenid)
    
    regression_Gauss_seenid = GC_node.regression(sl_seq_seenid[:,0:reg_num_signals], avg_labels)
    regressionMAE_Gauss_seenid = GC_node.regressionMAE(sl_seq_seenid[:,0:reg_num_signals], avg_labels)
    probs_seenid = GC_node.class_probabilities(sl_seq_seenid[:,0:reg_num_signals])
    softCR_Gauss_seenid = GC_node.softCR(sl_seq_seenid[:,0:reg_num_signals], correct_classes_seenid)
else:
    classes_Gauss_seenid = labels_Gauss_seenid = regression_Gauss_seenid = regressionMAE_Gauss_seenid = numpy.zeros(num_images_seenid) 
    probs_seenid = numpy.zeros((num_images_seenid, 2))
    softCR_Gauss_seenid = 0.0

if enable_kNN_cfr == True:
    print "kNN classify... (k=%d)"%kNN_k
    classes_kNN_seenid = numpy.array(kNN_node.label(sl_seq_seenid[:,0:reg_num_signals]))
    labels_kNN_seenid = more_nodes.map_class_numbers_to_avg_label(all_classes, avg_labels, classes_kNN_seenid)
else:
    classes_kNN_seenid = labels_kNN_seenid = numpy.zeros(num_images_seenid) 

if enable_svm_cfr == True:
    classes_svm_seenid = svm_node.label(svm_scale(sl_seq_seenid[:,0:reg_num_signals], data_mins, data_maxs, svm_min, svm_max))
#    regression_svm_seenid = svm_node.label_of_class(classes_svm_seenid)
#    regression2_svm_seenid = svm_node.regression(sl_seq_seenid[:,0:reg_num_signals])
#    regression3_svm_seenid = regression2_svm_seenid
    regression_svm_seenid = more_nodes.map_class_numbers_to_avg_label(all_classes, avg_labels, classes_svm_seenid)
    regression2_svm_seenid = more_nodes.map_class_numbers_to_avg_label(all_classes, avg_labels, classes_svm_seenid)
    regression3_svm_seenid = more_nodes.map_class_numbers_to_avg_label(all_classes, avg_labels, classes_svm_seenid)

#    regression3_svm_seenid = svm_node.eban_regression(sl_seq_seenid[:,0:reg_num_signals], hint=probs_seenid)
#    raw_input("please enter something to continue & save")
    
    #network_write.update_cache(probs_seenid, None, network_base_dir, "GCProbs", overwrite=True, use_hash=network_hash, verbose=True)

    
#    quit()
else:
    classes_svm_seenid=regression_svm_seenid = regression2_svm_seenid = regression3_svm_seenid = numpy.zeros(num_images_seenid)

#HACK
#classes_svm_seenid = svm_node.classifyNoMem(sl_seq_seenid[:,0:reg_num_signals])


       
if enable_lr_cfr == True:
    regression_lr_seenid = lr_node.execute(sl_seq_seenid[:,0:reg_num_signals]).flatten()
else:
    regression_lr_seenid = numpy.zeros(num_images_seenid)

if output_instead_of_SVM2:
    regression2_svm_seenid = (sl_seq_seenid[:,0] * orig_train_label_std) + orig_train_label_mean
    print "Applying cutoff to the label estimations for LR and Linear Scaling (SVM2)"
    regression2_svm_seenid = cutoff(regression2_svm_seenid, orig_train_label_min, orig_train_label_max)
    regression_lr_seenid = cutoff(regression_lr_seenid, orig_train_label_min, orig_train_label_max)

print "labels_kNN_seenid.shape=", labels_kNN_seenid.shape

#correct_labels_seenid = wider_1Darray(numpy.arange(iSeenid.MIN_GENDER, iSeenid.MAX_GENDER, iSeenid.GENDER_STEP), iSeenid.block_size)
print "correct_labels_seenid.shape=", correct_labels_seenid.shape
#correct_classes_seenid = numpy.arange(len(labels_ccc_seenid)) * len(labels_ccc_training) / len(labels_ccc_seenid) / block_size

t_class1 = time.time()
print "Classification/Regression over Seen Id in %0.3f s"% ((t_class1 - t_class0))


if integer_label_estimation:
    print "Making all label estimations for seenid data integer numbers"
    if convert_labels_days_to_years:
        labels_ncc_seenid = labels_ncc_seenid.astype(int)
        regression_Gauss_seenid = regression_Gauss_seenid.astype(int)
        regressionMAE_Gauss_seenid = regressionMAE_Gauss_seenid.astype(int)
        labels_kNN_seenid = labels_kNN_seenid.astype(int)
        regression_svm_seenid = regression_svm_seenid.astype(int)
        regression2_svm_seenid = regression2_svm_seenid.astype(int)
        regression3_svm_seenid = regression3_svm_seenid.astype(int)
        regression_lr_seenid = regression_lr_seenid.astype(int)
    else:
        labels_ncc_seenid = numpy.rint(labels_ncc_seenid)
        regression_Gauss_seenid = numpy.rint(regression_Gauss_seenid)
        regressionMAE_Gauss_seenid = numpy.rint(regressionMAE_Gauss_seenid)
        labels_kNN_seenid = numpy.rint(labels_kNN_seenid)
        regression_svm_seenid = numpy.rint(regression_svm_seenid)
        regression2_svm_seenid = numpy.rint(regression2_svm_seenid)
        regression3_svm_seenid = numpy.rint(regression3_svm_seenid)
        regression_lr_seenid = numpy.rint(regression_lr_seenid)
    print "regressionMAE_Gauss_seenid[0:5]=", regressionMAE_Gauss_seenid[0:5]

t10 = time.time()
t_load_images0 = time.time()
print "Loading test images, new ids..."

if coherent_seeds:
    numpy.random.seed(experiment_seed+555555)

image_files_newid = iNewid.input_files
num_images_newid = iNewid.num_images
block_size_newid = iNewid.block_size
seq = sNewid

if seq.input_files == "LoadBinaryData00":
    subimages_newid = load_natural_data(seq.data_base_dir, seq.base_filename, seq.samples, verbose=False)
elif seq.input_files == "LoadRawData":
    subimages_newid = load_raw_data(seq.data_base_dir, seq.base_filename, input_dim=seq.input_dim, dtype=seq.dtype, select_samples=seq.samples, verbose=False)
else:
#W
#    subimages_newid = experiment_datasets.load_data_from_sSeq(seq)
    subimages_newid = seq.load_data(seq)
#    subimages_newid = load_image_data(seq.input_files, seq.image_width, seq.image_height, seq.subimage_width, \
#                            seq.subimage_height, seq.pixelsampling_x, seq.pixelsampling_y, \
#                            seq.subimage_first_row, seq.subimage_first_column, seq.add_noise_L0, \
#                            seq.convert_format, seq.translations_x, seq.translations_y, seq.trans_sampled, background_type=seq.background_type, color_background_filter=filter, verbose=False)

t_load_images1 = time.time()
t11 = time.time()
print num_images_newid, " Images loaded in %0.3f s"% ((t_load_images1 - t_load_images0))

t_exec0 = time.time()
print "Execution over New Id testing set..."
print "Input Signal: New Id test images"
sl_seq_newid = flow.execute(subimages_newid)
sl_seq_newid = sl_seq_newid[:,skip_num_signals:]
if feature_cut_off_level > 0.0:  
    sl_seq_newid = cutoff(sl_seq_newid, min_cutoff, max_cutoff)

if clip_seenid_newid_to_training:
    print "clipping sl_seq_newid"
    sl_seq_newid_min = sl_seq_newid.min(axis=0)
    sl_seq_newid_max = sl_seq_newid.max(axis=0)
    print "sl_seq_training_min=", sl_seq_training_min
    print "sl_seq_training_max=", sl_seq_training_max   
    print "sl_seq_newid_min=", sl_seq_newid_min
    print "sl_seq_newid_max=", sl_seq_newid_max
    sl_seq_newid = numpy.clip(sl_seq_newid, sl_seq_training_min, sl_seq_training_max)


#WARNING!!!
#print "WARNING!!! SCALING NEW ID SLOW SIGNALS!!!"
#corr_factor = numpy.array([ 1.06273968,  1.0320762 ,  1.06581665,  1.01598426,  1.08355725,
#        1.10316477,  1.08731609,  1.05887109,  1.08185727,  1.09867758,
#        1.10567757,  1.08268021])
#print corr_factor
#
#corr_factor = numpy.array([ 1.06273968,  1.0320762 ,  1.06581665,  1.01598426,  1.08355725,
#        1.10316477,  1.08731609,  1.05887109,  1.08185727,  1.09867758]) * 0.98
#print corr_factor
#
#corr_factor =  numpy.sqrt(sl_seq_training.var(axis=0) / sl_seq_newid.var(axis=0))[0:reg_num_signals].mean()
#print corr_factor
#
#corr_factor =  numpy.sqrt(sl_seq_training.var(axis=0) / sl_seq_newid.var(axis=0))[0:reg_num_signals] * 0.98
#print corr_factor
#
#corr_factor =  0.977 * numpy.sqrt(sl_seq_training.var(axis=0)[0:reg_num_signals].mean() / sl_seq_newid.var(axis=0)[0:reg_num_signals].mean())
#print corr_factor

corr_factor=1.0
print corr_factor
sl_seq_newid[:,0:reg_num_signals] = sl_seq_newid[:,0:reg_num_signals] * corr_factor

t_exec1 = time.time()
print "Execution over New Id in %0.3f s"% ((t_exec1 - t_exec0))

t_class0 = time.time()

correct_classes_newid = iNewid.correct_classes
correct_labels_newid = iNewid.correct_labels

if convert_labels_days_to_years:
    if correct_labels_newid.mean() < 200:
        print "correct_labels_newid appears to be already year values (mean %f)"%correct_labels_newid.mean()
    else:
        print "converting correct_labels_newid from days to years"
        correct_labels_newid = correct_labels_newid / DAYS_IN_A_YEAR
        
    if integer_label_estimation:
        if (correct_labels_newid - correct_labels_newid.astype(int)).mean() < 0.01:
            print "correct_labels_newid appears to be already integer, preserving its value" 
        else:
            print "correct_labels_newid seem to be real values, converting them to years" 
            correct_labels_newid = (correct_labels_newid+0.0006).astype(int)
print "correct_labels_newid=", correct_labels_newid        

if enable_ncc_cfr == True:
    print "NCC classify..."
    classes_ncc_newid = numpy.array(ncc_node.label(sl_seq_newid[:,0:reg_num_signals]))
    labels_ncc_newid = more_nodes.map_class_numbers_to_avg_label(all_classes, avg_labels, classes_ncc_newid)
    print classes_ncc_newid
else:
    classes_ncc_newid = labels_ncc_newid = numpy.zeros(num_images_newid) 
           
if enable_ccc_Gauss_cfr == True:
#    classes_ccc_newid, labels_ccc_newid = S2SC.classifyCDC(sl_seq_newid[:,0:reg_num_signals])
#    classes_Gauss_newid, labels_Gauss_newid = S2SC.classifyGaussian(sl_seq_newid[:,0:reg_num_signals])
#    print "Classification of New Id test images: ", labels_ccc_newid
#    regression_Gauss_newid = S2SC.GaussianRegression(sl_seq_newid[:,0:reg_num_signals])
#    probs_newid = S2SC.GC_L0.class_probabilities(sl_seq_newid[:,0:reg_num_signals])

    classes_Gauss_newid = numpy.array(GC_node.label(sl_seq_newid[:,0:reg_num_signals]))
    labels_Gauss_newid = more_nodes.map_class_numbers_to_avg_label(all_classes, avg_labels, classes_Gauss_newid) 
    
    regression_Gauss_newid = GC_node.regression(sl_seq_newid[:,0:reg_num_signals], avg_labels)
    regressionMAE_Gauss_newid = GC_node.regressionMAE(sl_seq_newid[:,0:reg_num_signals], avg_labels)
    probs_newid = GC_node.class_probabilities(sl_seq_newid[:,0:reg_num_signals])
    softCR_Gauss_newid = GC_node.softCR(sl_seq_newid[:,0:reg_num_signals], correct_classes_newid)
else:
    classes_Gauss_newid = labels_Gauss_newid = regression_Gauss_newid = regressionMAE_Gauss_newid = numpy.zeros(num_images_newid) 
    probs_newid = numpy.zeros((num_images_newid, 2))
    softCR_Gauss_newid = 0.0

if enable_kNN_cfr == True:
    print "kNN classify... (k=%d)"%kNN_k
    classes_kNN_newid = numpy.array(kNN_node.label(sl_seq_newid[:,0:reg_num_signals]))
    labels_kNN_newid = more_nodes.map_class_numbers_to_avg_label(all_classes, avg_labels, classes_kNN_newid)
else:
    classes_kNN_newid = labels_kNN_newid = numpy.zeros(num_images_newid) 

if enable_svm_cfr == True:
    classes_svm_newid = svm_node.label(svm_scale(sl_seq_newid[:,0:reg_num_signals], data_mins, data_maxs, svm_min, svm_max))
    regression_svm_newid = more_nodes.map_class_numbers_to_avg_label(all_classes, avg_labels, classes_svm_newid)
    regression2_svm_newid = more_nodes.map_class_numbers_to_avg_label(all_classes, avg_labels, classes_svm_newid)
    regression3_svm_newid = more_nodes.map_class_numbers_to_avg_label(all_classes, avg_labels, classes_svm_newid)
#    regression_svm_newid = svm_node.label_of_class(classes_svm_newid)
#    regression2_svm_newid = svm_node.regression(sl_seq_newid[:,0:reg_num_signals])
#    regression3_svm_newid = regression2_svm_newid
#    regression3_svm_newid = svm_node.eban_regression(sl_seq_newid[:,0:reg_num_signals], hint=probs_newid)
#WARNING
#    regression3_svm_newid = svm_node.eban_regression3(sl_seq_newid[:,0:reg_num_signals], activation_func_app = my_sigmoid, hint=probs_newid)
#    raw_input("please enter something to continue")
    #Hack, reusing probs_newid for displaying probs_newid_eban_svm
#    probs_newid = svm_node.eban_probability2(sl_seq_seenid[:,0:reg_num_signals], hint=probs_seenid)
    probs_training[0, 10] = 1.0
    probs_newid[0, 10] = 1.0
    probs_seenid[0, 10] = 1.0
#    m_err1 = svm_node.model_error(probs, l)
else:
    classes_svm_newid=regression_svm_newid = regression2_svm_newid = regression3_svm_newid = numpy.zeros(num_images_newid)

#classes_svm_newid = svm_node.classifyNoMem(sl_seq_newid[:,0:reg_num_signals])

if enable_lr_cfr == True:
    regression_lr_newid = lr_node.execute(sl_seq_newid[:,0:reg_num_signals]).flatten()
else:
    regression_lr_newid = numpy.zeros(num_images_newid)

if output_instead_of_SVM2:
    regression2_svm_newid = (sl_seq_newid[:,0] * orig_train_label_std) + orig_train_label_mean
    print "Applying cutoff to the label estimations for LR and Linear Scaling (SVM2)"
    regression2_svm_newid = cutoff(regression2_svm_newid, orig_train_label_min, orig_train_label_max)
    regression_lr_newid = cutoff(regression_lr_newid, orig_train_label_min, orig_train_label_max)

t_class1 = time.time()
print "Classification/Regression over New Id in %0.3f s"% ((t_class1 - t_class0))

if integer_label_estimation:
#     print "WARNING, ADDING A BIAS OF -0.5 TO ESTIMATION OF NEWID ONLY!!!"
#     regression_Gauss_newid += -0.5
#     regressionMAE_Gauss_newid += -0.5
    
    print "Making all label estimations for newid data integer numbers"
    if convert_labels_days_to_years: #5.7 should be mapped to 5 years because age estimation is exact (days)
        labels_ncc_newid = labels_ncc_newid.astype(int)
        regression_Gauss_newid = regression_Gauss_newid.astype(int)
        regressionMAE_Gauss_newid = regressionMAE_Gauss_newid.astype(int)
        labels_kNN_newid = labels_kNN_newid.astype(int)
        regression_svm_newid = regression_svm_newid.astype(int)
        regression2_svm_newid = regression2_svm_newid.astype(int)
        regression3_svm_newid = regression3_svm_newid.astype(int)
        regression_lr_newid = regression_lr_newid.astype(int)
    else: #5.7 should be mapped to 6 years because age estimation is already based on years
        labels_ncc_newid = numpy.rint(labels_ncc_newid)
        regression_Gauss_newid = numpy.rint(regression_Gauss_newid)
        regressionMAE_Gauss_newid = numpy.rint(regressionMAE_Gauss_newid)
        labels_kNN_newid = numpy.rint(labels_kNN_newid)
        regression_svm_newid = numpy.rint(regression_svm_newid)
        regression2_svm_newid = numpy.rint(regression2_svm_newid)
        regression3_svm_newid = numpy.rint(regression3_svm_newid)
        regression_lr_newid = numpy.rint(regression_lr_newid)
        quit()
    print "regressionMAE_Gauss_newid[0:5]=", regressionMAE_Gauss_newid[0:5]



#print "Saving train/test_data for external analysis"
#ndarray_to_string(sl_seq_training, "/local/tmp/escalafl/training_samples.txt")
#ndarray_to_string(correct_labels_training, "/local/tmp/escalafl/training_labels.txt")
#ndarray_to_string(sl_seq_seenid, "/local/tmp/escalafl/seenid_samples.txt")
#ndarray_to_string(correct_labels_seenid, "/local/tmp/escalafl/seenid_labels.txt")
#ndarray_to_string(sl_seq_newid, "/local/tmp/escalafl/newid_samples.txt")
#ndarray_to_string(correct_labels_newid, "/local/tmp/escalafl/newid_labels.txt")

print "Computing typical delta, eta values for Training SFA Signal"
t_delta_eta0 = time.time()
results.typical_delta_train, results.typical_eta_newid = sfa_libs.comp_typical_delta_eta(sl_seq_training, iTrain.block_size, num_reps=200, training_mode=iTrain.train_mode)
results.brute_delta_train = sfa_libs.comp_delta_normalized(sl_seq_training)
results.brute_eta_train= sfa_libs.comp_eta(sl_seq_training)
t_delta_eta1 = time.time()
print "delta_train=", results.typical_delta_train
print "eta_train=", results.typical_eta_train
print "brute_delta_train=", results.brute_delta_train

print "Computing typical delta, eta values for New Id SFA Signal"
t_delta_eta0 = time.time()
results.typical_delta_newid, results.typical_eta_newid = sfa_libs.comp_typical_delta_eta(sl_seq_newid, iNewid.block_size, num_reps=200, training_mode=iNewid.train_mode)
results.brute_delta_newid = sfa_libs.comp_delta_normalized(sl_seq_newid)
results.brute_eta_newid= sfa_libs.comp_eta(sl_seq_newid)
t_delta_eta1 = time.time()
print "typical_delta_newid=", results.typical_delta_newid
print "typical_delta_newid[0:31].sum()=", results.typical_delta_newid[0:31].sum()
print "typical_eta_newid=", results.typical_eta_newid
print "brute_delta_newid=", results.brute_delta_newid
#print "brute_eta_newid=", results.brute_eta_newid
print "computed delta/eta in %0.3f ms"% ((t_delta_eta1-t_delta_eta0)*1000.0)


#print "Generating (new random) input sequence..."
#use_average = False
#use_first_id = False
#use_random_walk = False
#use_training_data = True
#use_new_identity = False
#new_id = 5
#if block_size_exec is not None and block_size_exec > 1:
#    print "block_size_exec > 1"
#    num_images2 = num_images / block_size_exec
#    subimages2 = numpy.zeros((num_images2, subimage_width * subimage_height))
#    if use_first_id is True:-1 to 1 or?
#        print "Input Signal: First ID / First Pose of each ID"
#        for i in range(num_images2):
#            subimages2[i] = subimages[block_size_exec * i]       
#    elif use_average is True:
#        print "Input Signal: Average of IDs"
#        for i in range(num_images2):
#            subimages2[i] = subimages[block_size_exec * i: block_size_exec * (i+1)].sum(axis=0) / block_size_exec
#    elif use_random_walk is True:
#        print "Input Signal: Random Walk"
#        for i in range(num_images2):
#            id = numpy.random.randint(block_size_exec)
##            subimages[block_size * i + id]
##            subimages2[i] = subimages[0]
#            subimages2[i] = subimages[block_size_exec * i + id]
#    elif use_training_data is True:
#        print "Input Signal: Training Data"
#        subimages2 = subimages
#        num_images2 = num_images
#    elif use_new_identity is True:
#        print "Input Signal: New ID random%03d*.tif"%(new_id)
#        test_image_files1 = glob.glob(im_seq_base_dir + "/random%03d*.tif"%(new_id))
#        test_image_files1.sort()
#
#        test_image_files = []
#        for i in range(len(test_image_files1)):
#            test_image_files.append(test_image_files1[i])
#
#        num_images2 = num_test_images = len(test_image_files)
#        
#        subimages2 = numpy.zeros((num_test_images, subimage_width * subimage_height))
#        act_im_num = 0
#        for image_file in test_image_files:
#            im = Image.open(image_file)
#            im = im.convert("L")
#            im_arr = numpy.asarray(im)
#            im_small = im_arr[subimage_first_row:(subimage_first_row+subimage_height*subimage_pixelsampling):subimage_pixelsampling,
#                              subimage_first_column:(subimage_first_column+subimage_width*subimage_pixelsampling):subimage_pixelsampling].astype(float)
#            subimages2[act_im_num] = im_small.flatten()
#            act_im_num = act_im_num+1
#            del im_small
#            del im_arr
#            del im
#    else:
#        print "******************* No input sequence specified !!!!!!!!!!!!!!!!!"
##
#    subimages = subimages2
#    num_images = num_images2
#
##flow.
##print "Training finished, ed in %0.3f ms"% ((t2-t1)*1000.0)
#sl_seq = flow.execute(subimages)
#inverted_im = flow.inverse(sl_seq)

if isinstance(block_size, int):
    print "virtual sequence length complete = ", num_images_training  * (block_size - 1)/2
    print "virtual sequence length sequence = ", (num_images_training - block_size)  * block_size 
    print "virtual sequence length mixed = ", num_images_training  * (block_size - 1)/2 + (num_images_training - block_size)  * block_size
else:
    print "length of virtual sequence not computed = "

save_train_data=True and False #This fails for large datasets :( TODO: Make this an option
if save_train_data:
    uniqueness = numpy.random.randint(32000)
    save_dir_subimages_features_training = "/local/tmp/escalafl/Alberto/saved_images_features_training"
    print "Using uniqueness %d for saving subimage and feature data"%uniqueness
    cache.pickle_array(subimages_train, base_dir=save_dir_subimages_features_training, base_filename="subimages_train%5d"%uniqueness, chunk_size=5000, block_size=1, continuous=False, overwrite=True, verbose=True)
    cache.pickle_array(sl_seq_training, base_dir=save_dir_subimages_features_training, base_filename="sl_seq_training%5d"%uniqueness, chunk_size=5000, block_size=1, continuous=False, overwrite=True, verbose=True)
#Then unpicke with unpickle_array(base_dir="", base_filename="subimages_train%5d"%uniqueness):
    

print "Estimating explained variance for Train SFA Signal"
number_samples_explained_variance = 9000 #1000 #4000 #2000
#fast_inverse_available = True and False

#WARNING!!!!
if estimate_explained_var_with_inverse:
#    print "Estimated explained variance with inverse (train) is: ", more_nodes.estimated_explained_variance(subimages_train, flow, sl_seq_training, number_samples_explained_variance)
    print "Estimated explained variance with inverse (train) is: ", more_nodes.estimated_explained_variance(subimages_train, flow, sl_seq_training, number_samples_explained_variance)
    print "Estimated explained variance with inverse (newid) is: ", more_nodes.estimated_explained_variance(subimages_newid, flow, sl_seq_newid, number_samples_explained_variance)
else:
    print "Fast inverse not available, not estimating explained variance"

if estimate_explained_var_with_kNN_k:
    k = estimate_explained_var_with_kNN_k #  k=64
#    print "Estimated explained variance with kNN (train, %d features) is: "%reg_num_signals, more_nodes.estimated_explained_var_with_kNN(subimages_train, sl_seq_training[:,0:reg_num_signals], max_num_samples_for_ev = 4000, max_test_samples_for_ev=2000, k=8, ignore_closest_match = True, label_avg=True)
    print "Estimated explained variance with kNN (train, %d features) is: "%reg_num_signals, more_nodes.estimated_explained_var_with_kNN(subimages_train, sl_seq_training[:,0:reg_num_signals], max_num_samples_for_ev = 10000, max_test_samples_for_ev=10000, k=k, ignore_closest_match = True, operation="average")
else:
    print "Not estimating explained variance with kNN"

if estimate_explained_var_with_kNN_lin_app_k:
    k= estimate_explained_var_with_kNN_lin_app_k #k=64
#    print "Estimated explained variance with kNN (train, %d features) is: "%reg_num_signals, more_nodes.estimated_explained_var_with_kNN(subimages_train, sl_seq_training[:,0:reg_num_signals], max_num_samples_for_ev = 4000, max_test_samples_for_ev=2000, k=8, ignore_closest_match = True, label_avg=True)
    print "Estimated explained variance with kNN_lin_app (train, %d features) is: "%reg_num_signals, more_nodes.estimated_explained_var_with_kNN(subimages_train, sl_seq_training[:,0:reg_num_signals], max_num_samples_for_ev = 10000, max_test_samples_for_ev=10000, k=k, ignore_closest_match = True, operation="lin_app")
else:
    print "Not estimating explained variance with kNN_lin_app"

if estimate_explained_var_linear_global_N:
    if estimate_explained_var_linear_global_N > 0:
        number_samples_EV_linear_global = estimate_explained_var_linear_global_N
    else:
        number_samples_EV_linear_global = sl_seq_training.shape[0]
#    num_features = sl_seq_training.shape[1]
    #WARNING!
    #OFFICIAL AGE IS THIS:
    #EVLinGlobal_train1, EVLinGlobal_train2, EVLinGlobal_newid = more_nodes.estimate_explained_var_linear_global(subimages_train, sl_seq_training[:,0:40], subimages_newid, sl_seq_newid[:,0:40], num_features, number_samples_EV_linear_global)
    #FEATURE OBFUSCATION TEST:
    number_samples_EV_linear_global = sl_seq_seenid.shape[0]
    num_features_linear_model = 75
    EVLinGlobal_train1, EVLinGlobal_train2, EVLinGlobal_newid = more_nodes.estimate_explained_var_linear_global(subimages_seenid, sl_seq_seenid[:,0:num_features_linear_model], subimages_newid, sl_seq_newid[:,0:num_features_linear_model], num_features_linear_model, number_samples_EV_linear_global)

    print "Explained Variance Linear Global for training data (%d features, subset of size %d) is: "%(num_features_linear_model, number_samples_EV_linear_global) , EVLinGlobal_train1, 
    print "for training data (new random subset) is: ", EVLinGlobal_train2
    print "for newid (all_samples FORCED %d) is: "%num_features_linear_model, EVLinGlobal_newid
else:
    print "Not estimating explained variance with global linear reconstruction"
    num_features_linear_model = 75
    
print "Computing chance levels for newid data"
chance_level_RMSE_newid = correct_labels_newid.std()
correct_labels_newid_sorted = correct_labels_newid + 0.0
correct_labels_newid_sorted.sort()
median_estimation = numpy.ones(len(correct_labels_newid)) * correct_labels_newid_sorted[len(correct_labels_newid)/2]
chance_level_MAE_newid = classifiers.mean_average_error(correct_labels_newid, median_estimation) 
print "chance_level_RMSE_newid=", chance_level_RMSE_newid, "chance_level_MAE_newid=", chance_level_MAE_newid
print "correct_labels_newid.mean()=", correct_labels_newid.mean(), "correct_labels_newid median() ",  median_estimation
print "Computations Finished!"


print "** Displaying Benchmark data: **"
for task_name, task_time in benchmark:
    print "     ", task_name, " done in %0.3f s"%task_time
 
  
print "Classification/Regression Performance: "
if Parameters.analysis != False or True:
    print correct_classes_training
    print classes_kNN_training
    #MSE
    results.class_ncc_rate_train = classifiers.correct_classif_rate(correct_classes_training, classes_ncc_training)
    results.class_kNN_rate_train = classifiers.correct_classif_rate(correct_classes_training, classes_kNN_training)
    results.class_Gauss_rate_train = classifiers.correct_classif_rate(correct_classes_training, classes_Gauss_training)
    results.class_svm_rate_train = classifiers.correct_classif_rate(correct_classes_training, classes_svm_training)
    results.mse_ncc_train = distance_squared_Euclidean(correct_labels_training, labels_ncc_training) / len(labels_kNN_training)
    results.mse_kNN_train = distance_squared_Euclidean(correct_labels_training, labels_kNN_training) / len(labels_kNN_training)
    results.mse_gauss_train = distance_squared_Euclidean(correct_labels_training, regression_Gauss_training)/len(labels_kNN_training)
    results.mse_svm_train = distance_squared_Euclidean(correct_labels_training, regression_svm_training)/len(labels_kNN_training)
    results.mse2_svm_train = distance_squared_Euclidean(correct_labels_training, regression2_svm_training)/len(labels_kNN_training)
    results.mse3_svm_train = distance_squared_Euclidean(correct_labels_training, regression3_svm_training)/len(labels_kNN_training)
    results.mse_lr_train = distance_squared_Euclidean(correct_labels_training, regression_lr_training)/len(labels_kNN_training)
    #MAE
    results.maeOpt_gauss_train = classifiers.mean_average_error(correct_labels_training, regressionMAE_Gauss_training)
    results.mae_gauss_train = classifiers.mean_average_error(regression_Gauss_training, correct_labels_training)
    #RMSE
    results.rmse_ncc_train = results.mse_ncc_train ** 0.5
    results.rmse_kNN_train = results.mse_kNN_train ** 0.5
    results.rmse_gauss_train =  results.mse_gauss_train ** 0.5
    results.rmse_svm_train = results.mse_svm_train ** 0.5
    results.rmse2_svm_train = results.mse2_svm_train ** 0.5
    results.rmse3_svm_train = results.mse3_svm_train ** 0.5
    results.rmse_lr_train = results.mse_lr_train ** 0.5
    
    results.class_ncc_rate_seenid = classifiers.correct_classif_rate(correct_classes_seenid, classes_ncc_seenid)
    results.class_kNN_rate_seenid = classifiers.correct_classif_rate(correct_classes_seenid, classes_kNN_seenid)
    results.class_Gauss_rate_seenid = classifiers.correct_classif_rate(correct_classes_seenid, classes_Gauss_seenid)
    results.class_svm_rate_seenid = classifiers.correct_classif_rate(correct_classes_seenid, classes_svm_seenid)
    results.mse_ncc_seenid = distance_squared_Euclidean(correct_labels_seenid, labels_ncc_seenid)/len(labels_kNN_seenid)
    results.mse_kNN_seenid = distance_squared_Euclidean(correct_labels_seenid, labels_kNN_seenid)/len(labels_kNN_seenid)
    results.mse_gauss_seenid = distance_squared_Euclidean(correct_labels_seenid, regression_Gauss_seenid)/len(labels_kNN_seenid)
    results.maeOpt_gauss_seenid = classifiers.mean_average_error(correct_labels_seenid, regressionMAE_Gauss_seenid)
    results.mse_svm_seenid = distance_squared_Euclidean(correct_labels_seenid, regression_svm_seenid)/len(labels_kNN_seenid)
    results.mse2_svm_seenid = distance_squared_Euclidean(correct_labels_seenid, regression2_svm_seenid)/len(labels_kNN_seenid)
    results.mse3_svm_seenid = distance_squared_Euclidean(correct_labels_seenid, regression3_svm_seenid)/len(labels_kNN_seenid)
    results.mse_lr_seenid = distance_squared_Euclidean(correct_labels_seenid, regression_lr_seenid)/len(labels_kNN_seenid)
    results.mae_gauss_seenid = classifiers.mean_average_error(regression_Gauss_seenid, correct_labels_seenid)
  
    results.rmse_ncc_seenid = results.mse_ncc_seenid ** 0.5
    results.rmse_kNN_seenid = results.mse_kNN_seenid ** 0.5
    results.rmse_gauss_seenid = results.mse_gauss_seenid ** 0.5
    results.rmse_svm_seenid = results.mse_svm_seenid ** 0.5
    results.rmse2_svm_seenid = results.mse2_svm_seenid ** 0.5
    results.rmse3_svm_seenid = results.mse3_svm_seenid ** 0.5
    results.rmse_lr_seenid = results.mse_lr_seenid ** 0.5
  
    print correct_classes_newid.shape, classes_kNN_newid.shape
    results.class_ncc_rate_newid = classifiers.correct_classif_rate(correct_classes_newid, classes_ncc_newid)
    results.class_kNN_rate_newid = classifiers.correct_classif_rate(correct_classes_newid, classes_kNN_newid)
    results.class_Gauss_rate_newid = classifiers.correct_classif_rate(correct_classes_newid, classes_Gauss_newid)
    results.class_svm_rate_newid = classifiers.correct_classif_rate(correct_classes_newid, classes_svm_newid)
    results.mse_ncc_newid = distance_squared_Euclidean(correct_labels_newid, labels_ncc_newid)/len(labels_kNN_newid)
    results.mse_kNN_newid = distance_squared_Euclidean(correct_labels_newid, labels_kNN_newid)/len(labels_kNN_newid)
    results.mse_gauss_newid = distance_squared_Euclidean(correct_labels_newid, regression_Gauss_newid)/len(labels_kNN_newid)
    results.maeOpt_gauss_newid = classifiers.mean_average_error(correct_labels_newid, regressionMAE_Gauss_newid)
    results.mse_svm_newid = distance_squared_Euclidean(correct_labels_newid, regression_svm_newid)/len(labels_kNN_newid)
    results.mse2_svm_newid = distance_squared_Euclidean(correct_labels_newid, regression2_svm_newid)/len(labels_kNN_newid)
    results.mse3_svm_newid = distance_squared_Euclidean(correct_labels_newid, regression3_svm_newid)/len(labels_kNN_newid)
    results.mse_lr_newid = distance_squared_Euclidean(correct_labels_newid, regression_lr_newid)/len(labels_kNN_newid)
    results.mae_gauss_newid = classifiers.mean_average_error(correct_labels_newid, regression_Gauss_newid)

    results.rmse_ncc_newid = results.mse_ncc_newid ** 0.5
    results.rmse_kNN_newid = results.mse_kNN_newid ** 0.5
    results.rmse_gauss_newid = results.mse_gauss_newid ** 0.5
    results.rmse_svm_newid = results.mse_svm_newid ** 0.5
    results.rmse2_svm_newid = results.mse2_svm_newid ** 0.5
    results.rmse3_svm_newid = results.mse3_svm_newid ** 0.5
    results.rmse_lr_newid = results.mse_lr_newid ** 0.5

print "Comparisson of MAE for RMSE estimation and MAE estimation"
print "regression_Gauss_newid[100:150] =", regression_Gauss_newid[100:150]
print "regressionMAE_Gauss_newid[100:150] =", regressionMAE_Gauss_newid[100:150]
print "diff MAE-RMSE= ", regressionMAE_Gauss_newid[100:150]-regression_Gauss_newid[100:150]
worst = numpy.argsort(numpy.abs(regressionMAE_Gauss_newid-regression_Gauss_newid))
print "worst[-50:] diff MAE-RMSE= ", worst[-50:]
print "regression_Gauss_newid[worst[-50:]]=", regression_Gauss_newid[worst[-50:]]
print "regressionMAE_Gauss_newid[worst[-50:]]=", regressionMAE_Gauss_newid[worst[-50:]]
print "correct_labels_newid[worst[-50:]]=", correct_labels_newid[worst[-50:]]

results.maeOpt_gauss_newid = classifiers.mean_average_error(correct_labels_newid, regressionMAE_Gauss_newid)
results.mae_gauss_newid =    classifiers.mean_average_error(correct_labels_newid, regression_Gauss_newid)
    
print "N1=", classifiers.mean_average_error(correct_labels_newid, regressionMAE_Gauss_newid)
print "N2=", classifiers.mean_average_error(correct_labels_newid, regression_Gauss_newid)
numpy.savetxt("regressionMAE_Gauss_newid", regressionMAE_Gauss_newid)
numpy.savetxt("regression_Gauss_newid", regression_Gauss_newid)
numpy.savetxt("correct_labels_newid", correct_labels_newid)

cs_list =  {}
if cumulative_scores:
    largest_errors = numpy.arange(0, 31)
    print "Computing cumulative errors cs()= {", 
    for largest_error in largest_errors:
        cs = more_nodes.cumulative_score(ground_truth=correct_labels_newid, estimation=regression_Gauss_newid, largest_error=largest_error, integer_rounding=True)
        cs_list[largest_error] = cs
        print "%d:%0.7f, "%(largest_error, cs),
    print "}"
results.cs_list = cs_list


error_table =  {}
maes = {}
estimation_means = {}
print "Error table:"
if cumulative_scores:
    different_labels = numpy.unique(correct_labels_newid)
    for label in different_labels:
        error_table[label]={}
        indices = (correct_labels_newid == label)
        errors = correct_labels_newid[indices] - regression_Gauss_newid[indices]    
        abs_errors = numpy.abs(errors)
      
        estimation_means[label] = regression_Gauss_newid[indices].mean()

        for error in numpy.unique(errors):
            error_table[label][error] = 0

        maes[label] = abs_errors.mean()
#0
#        for abs_error in abs_errors:
#            maes[label] += abs_error
#        maes[label] /= 1.0 * len(errors)

        print ""   
        print "label=", label,       
        for error in errors:
            error_table[label][error] = error_table[label][error] + 1

        for error in numpy.unique(errors):
            print "e[%d]=%d "%(error, error_table[label][error]),

    #Now compute error frequencies for all labels simultaneuous
    signed_errors={}
    for error in numpy.arange(-200,200):
        signed_errors[error]=0
    for label in different_labels:
        for error in error_table[label].keys():
            signed_errors[error] = signed_errors[error] + error_table[label][error]

    print "\n Global signed errors:" 
    signed_error_keys = numpy.array(signed_errors.keys())
    signed_error_keys.sort()
    for error in signed_error_keys:
        print "e[%d]=%d "%(error, signed_errors[error]),
    print "."


    print "\n MAES for each GT year. maes(%d) to maes(%d)"%(different_labels[0],different_labels[-1])
    for label in different_labels:
        print "%f, "%maes[label],

    print "\n estimation means for each GT year. estim_means(%d) to estim_means(%d)"%(different_labels[0],different_labels[-1])
    for label in different_labels:
        print "%f, "%estimation_means[label],


if confusion_matrix and integer_label_estimation:
    print "Computing confusion matrix"
    min_label = numpy.min((correct_labels_training.min(), correct_labels_seenid.min(), correct_labels_newid.min())).astype(int)
    max_label = numpy.max((correct_labels_training.max(), correct_labels_seenid.max(), correct_labels_newid.max())).astype(int)
    print "overriding min/max label from data (%d, %d) to (16,77)"%(min_label, max_label)
    min_label = 16
    max_label = 77

    different_labels = numpy.arange(min_label, max_label+1, dtype=int)
    num_diff_labels = max_label-min_label+1

    confusion = numpy.zeros((num_diff_labels,num_diff_labels))
    mask_gt = {}
    for ii, l_gt in enumerate(different_labels):
        mask_gt[ii] = (correct_labels_newid == l_gt)
    mask_est = {}    
    for jj, l_est in enumerate(different_labels):
        mask_est[jj] = (regression_Gauss_newid == l_est)
    for ii, l_gt in enumerate(different_labels):
        for jj, l_est in enumerate(different_labels):
            confusion[ii,jj] = (mask_gt[ii] * mask_est[jj]).sum()

    print "confusion:=", confusion
    
    #Output confusion matrix to standard output
    for label in different_labels:
        print "%f, "%label,
    print ""
    for ii in range(num_diff_labels):
        print "[",
        for jj in range(num_diff_labels):
            print "%d, "%confusion[ii,jj],
        print "]"

    print "sums:",
    for ii in range(num_diff_labels):
        print "%d, "%mask_gt[ii].sum(),
    print "]"
save_results=False
if save_results:
    cache.pickle_to_disk(results, "results_" + str(int(time.time()))+ ".pckl")

if False:
    print "sl_seq_training.mean(axis=0)=", sl_seq_training.mean(axis=0)
    print "sl_seq_seenid.mean(axis=0)=", sl_seq_seenid.mean(axis=0)
    print "sl_seq_newid.mean(axis=0)=", sl_seq_newid.mean(axis=0)
    print "sl_seq_training.var(axis=0)=", sl_seq_training.var(axis=0)
    print "sl_seq_seenid.var(axis=0)=", sl_seq_seenid.var(axis=0)
    print "sl_seq_newid.var(axis=0)=", sl_seq_newid.var(axis=0)
    
print "Train: %0.3f CR_NCC, %0.3f CR_kNN, CR_Gauss %0.5f, softCR_Gauss=%0.5f, CR_SVM %0.3f, MSE_NCC %0.3f, MSE_kNN %0.3f, MSE_Gauss= %0.3f MSE3_SVM %0.3f, MSE2_SVM %0.3f, MSE_SVM %0.3f, MSE_LR %0.3f, MAE= %0.5f MAE(Opt)= %0.3f"%(
       results.class_ncc_rate_train, results.class_kNN_rate_train, results.class_Gauss_rate_train, softCR_Gauss_training, results.class_svm_rate_train, results.mse_ncc_train, results.mse_kNN_train, results.mse_gauss_train, 
       results.mse3_svm_train, results.mse2_svm_train, results.mse_svm_train, results.mse_lr_train, results.mae_gauss_train, results.maeOpt_gauss_train)
print "Seen Id: %0.3f CR_NCC, %0.3f CR_kNN, CR_Gauss %0.5f, softCR_Gauss=%0.5f, CR_SVM %0.3f, MSE_NCC %0.3f, MSE_kNN %0.3f, MSE_Gauss= %0.3f MSE3_SVM %0.3f, MSE2_SVM %0.3f, MSE_SVM %0.3f, MSE_LR %0.3f, MAE= %0.5f MAE(Opt)= %0.3f"%(
        results.class_ncc_rate_seenid, results.class_kNN_rate_seenid, results.class_Gauss_rate_seenid, softCR_Gauss_seenid, results.class_svm_rate_seenid, results.mse_ncc_seenid, results.mse_kNN_seenid, results.mse_gauss_seenid, 
        results.mse3_svm_seenid, results.mse2_svm_seenid, results.mse_svm_seenid, results.mse_lr_seenid, results.mae_gauss_seenid, results.maeOpt_gauss_seenid)
print "New Id: %0.3f CR_NCC, %0.3f CR_kNN, CR_Gauss %0.5f, softCR_Gauss=%0.5f, CR_SVM %0.3f, MSE_NCC %0.3f, MSE_kNN %0.3f, MSE_Gauss= %0.3f MSE3_SVM %0.3f, MSE2_SVM %0.3f, MSE_SVM %0.3f, MSE_LR %0.3f , MAE= %0.5f MAE(Opt)= %0.3f"%(
        results.class_ncc_rate_newid, results.class_kNN_rate_newid, results.class_Gauss_rate_newid, softCR_Gauss_newid, results.class_svm_rate_newid, results.mse_ncc_newid, results.mse_kNN_newid, results.mse_gauss_newid, 
        results.mse3_svm_newid, results.mse2_svm_newid, results.mse_svm_newid, results.mse_lr_newid, results.mae_gauss_newid, results.maeOpt_gauss_newid)

print "Train:   RMSE_NCC %0.3f, RMSE_kNN %0.3f, RMSE_Gauss= %0.5f RMSE3_SVM %0.3f, RMSE2_SVM %0.3f, RMSE_SVM %0.3f, RMSE_LR %0.3f"%(
       results.rmse_ncc_train, results.rmse_kNN_train, results.rmse_gauss_train, 
       results.rmse3_svm_train, results.rmse2_svm_train, results.rmse_svm_train, results.rmse_lr_train)
print "Seen Id: RMSE_NCC %0.3f, RMSE_kNN %0.3f, RMSE_Gauss= %0.5f RMSE3_SVM %0.3f, RMSE2_SVM %0.3f, RMSE_SVM %0.3f, RMSE_LR %0.3f"%(
        results.rmse_ncc_seenid, results.rmse_kNN_seenid, results.rmse_gauss_seenid, 
        results.rmse3_svm_seenid, results.rmse2_svm_seenid, results.rmse_svm_seenid, results.rmse_lr_seenid)
print "New Id:  RMSE_NCC %0.3f, RMSE_kNN %0.3f, RMSE_Gauss= %0.5f RMSE3_SVM %0.3f, RMSE2_SVM %0.3f, RMSE_SVM %0.3f, RMSE_LR %0.3f"%(
        results.rmse_ncc_newid, results.rmse_kNN_newid, results.rmse_gauss_newid, 
        results.rmse3_svm_newid, results.rmse2_svm_newid, results.rmse_svm_newid, results.rmse_lr_newid)   
    
if False:
    starting_point= "Sigmoids" #None, "Sigmoids", "Identity"
    print "Computations useful to determine information loss and feature obfuscation IL/FO... starting_point=", starting_point
    if iTrain.train_mode == "clustered":
        if features_residual_information > 0:
            results_e1_e2_from_feats=[]
            for num_feats_residual_information in numpy.arange(40,features_residual_information,5):
                e1, e2 = more_nodes.compute_classification_performance(sl_seq_seenid, correct_classes_seenid, sl_seq_newid, correct_classes_newid, num_feats_residual_information, starting_point=starting_point)
                #print "Classification rates on expanded slow features with dimensionality %d are %f for training and %f for test"%(num_feats_residual_information, e1, e2)
                results_e1_e2_from_feats.append((num_feats_residual_information, e1,e2))
            print "\n num_feats_residual_information =",
            for (num_feats_residual_information, e1, e2) in  results_e1_e2_from_feats:
                print num_feats_residual_information,", ",
            print "\n classification rate on seenid(feats) =",
            for (num_feats_residual_information, e1, e2) in  results_e1_e2_from_feats:
                print "%f, "%e1,
            print "\n classification rate on newid(feats) =",
            for (num_feats_residual_information, e1, e2) in  results_e1_e2_from_feats:
                print "%f, "%e2,
    
        if compute_input_information:
            results_e1_e2_from_pca=[]
            pca_node = mdp.nodes.PCANode(output_dim=0.99)
            pca_node.train(subimages_seenid)
            pca_node.stop_training()
            subimages_seenid_pca = pca_node.execute(subimages_seenid)
            subimages_newid_pca = pca_node.execute(subimages_newid)
            print "\n *****subimages_newid_pca.shape", subimages_newid_pca.shape
            for num_feats_residual_information in numpy.arange(40,150,5): #(40,150,5):
                e1, e2 = more_nodes.compute_classification_performance(subimages_seenid_pca, correct_classes_seenid, subimages_newid_pca, correct_classes_newid, num_feats_residual_information, starting_point=starting_point)
                #print "Classification rates on expanded input data with dimensionality %d are %f for training and %f for test"%(num_feats_residual_information, e1, e2)
                results_e1_e2_from_pca.append((num_feats_residual_information, e1,e2))
            print "\n num_feats_residual_information =",
            for (num_feats_residual_information, e1, e2) in  results_e1_e2_from_pca:
                print num_feats_residual_information,", ",
            print "\n classification rate on seenid(input) =",
            for (num_feats_residual_information, e1, e2) in  results_e1_e2_from_pca:
                print "%f, "%e1,
            print "\n classification rate on newid(input) =",
            for (num_feats_residual_information, e1, e2) in  results_e1_e2_from_pca:
                print "%f, "%e2,
            print "\n max CR on newid(input) = ", numpy.max([e2 for (nf, e1, e2) in results_e1_e2_from_pca])
    else:
        if features_residual_information > 0:
            for num_feats_residual_information in numpy.linspace(60,features_residual_information,11):
                e1, e2 = more_nodes.compute_regression_performance(sl_seq_seenid, correct_labels_seenid, sl_seq_newid, correct_labels_newid, num_feats_residual_information, starting_point=starting_point)
                print "RMSE on expanded slow features with dimensionality %d are %f for training and %f for test"%(num_feats_residual_information, e1, e2)
        
        if compute_input_information:
            for num_feats_residual_information in numpy.linspace(144,features_residual_information,11):
                e1, e2 = more_nodes.compute_regression_performance(subimages_seenid, correct_labels_seenid, subimages_newid, correct_labels_newid, num_feats_residual_information, starting_point=starting_point)
                print "RMSE on expanded input data with dimensionality %d are %f for training and %f for test"%(num_feats_residual_information, e1, e2)


#quit()
scale_disp = 1

print "Computing average SFA..."
if isinstance(iTrain.block_size, int):
    num_blocks_train = iTrain.num_images/iTrain.block_size
elif iTrain.block_size!=None:
    num_blocks_train = len(iTrain.block_size)
else:
    num_blocks_train = iTrain.num_images

print num_blocks_train, hierarchy_out_dim, sl_seq_training.shape, block_size, iTrain.block_size

sl_seq_training_mean = numpy.zeros((num_blocks_train, hierarchy_out_dim))
if isinstance(iTrain.block_size, int):
    for block in range(num_blocks_train):
        sl_seq_training_mean[block] = sl_seq_training[block*block_size:(block+1)*block_size,:].mean(axis=0)
else:
    counter_sl = 0
    for block in range(num_blocks_train):
        sl_seq_training_mean[block] = sl_seq_training[counter_sl:counter_sl + iTrain.block_size[block],:].mean(axis=0)
        counter_sl += iTrain.block_size[block]

print "%d Blocks used for averages"%num_blocks_train

#Function for gender label estimation. (-3 to -0.1) = Masculine, (0.0 to 2.9) = femenine. Midpoint between classes is -0.05
def binarize_array(arr):
    arr2 = arr + 0.0
    arr2[arr2 < -0.05]=-1
    arr2[arr2 >= -0.05]=1
    return arr2

if Parameters == experiment_datasets.ParamsGender or experiment_datasets.ParamsRAgeFunc:
    print "Computing effective gender recognition:"
    binary_gender_estimation_training = binarize_array(regression_Gauss_training)
    binary_correct_labels_training = binarize_array(correct_labels_training)
    binary_gender_estimation_rate_training = classifiers.correct_classif_rate(binary_correct_labels_training, binary_gender_estimation_training) 
    print "Binary gender classification rate (training) from continuous labels is:", binary_gender_estimation_rate_training
    binary_gender_estimation_seenid = binarize_array(regression_Gauss_seenid)
    binary_correct_labels_seenid = binarize_array(correct_labels_seenid)
    binary_gender_estimation_rate_seenid = classifiers.correct_classif_rate(binary_correct_labels_seenid, binary_gender_estimation_seenid) 
    print "Binary gender classification rate (seenid) from continuous labels is:", binary_gender_estimation_rate_seenid
    binary_gender_estimation_newid = binarize_array(regression_Gauss_newid)
    binary_correct_labels_newid = binarize_array(correct_labels_newid)
    binary_gender_estimation_rate_newid = classifiers.correct_classif_rate(binary_correct_labels_newid, binary_gender_estimation_newid) 
    print "Binary gender classification rate (newid) from continuous labels is:", binary_gender_estimation_rate_newid

    
if Parameters == experiment_datasets.ParamsRGTSRBFunc and output_filename != None:
    fd = open("G"+output_filename, "w")
    txt = ""
    for i, filename in enumerate(iNewid.input_files):
        txt += filename[-9:] +"; "+str(int(classes_Gauss_newid[i]))+"\n"
#    print "writing \"%s\" to; %s"%(txt, output_filename)
    fd.write(txt)
    fd.close()

    fd = open("C"+output_filename, "w")
    txt = ""
    for i, filename in enumerate(iNewid.input_files):
        txt += filename[-9:] +"; "+str(int(classes_kNN_newid[i])) + "\n"
#    print "writing \"%s\" to; %s"%(txt, output_filename)
    fd.write(txt)
    fd.close()

    fd = open("NN"+output_filename, "w")
    txt = ""
    for i, filename in enumerate(iNewid.input_files):
        txt += filename[-9:] +"; "+str(int(classes_svm_newid[i])) + "\n"
#    print "writing \"%s\" to; %s"%(txt, output_filename)
    fd.write(txt)
    fd.close()

    save_SFA_Features = True and (Parameters.activate_HOG == False) #Will only overwrite SFA features when running in SFA mode

    sfa_output_dir="/local/escalafl/Alberto/GTSRB/Online-Test/SFA/SFA_02/"
    GTSRB_SFA_dir_training = "/local/escalafl/Alberto/GTSRB/GTSRB_Features_SFA/training"
    GTSRB_SFA_dir_OnlineTest = "/local/escalafl/Alberto/GTSRB/Online-Test/SFA" 
    
    #/local/escalafl/Alberto/GTSRB/Online-Test/SFA/SFA_02
    number_SFA_features = 98
    if save_SFA_Features:
        iSeq_sl_tuples = [(iTrain, sl_seq_training),(iSeenid, sl_seq_seenid),(iNewid, sl_seq_newid)]
        for iSeq, sl in iSeq_sl_tuples:
            online_base_dir = "/local/escalafl/Alberto/GTSRB/Online-Test/Images"
            if iSeq.input_files[0][0:len(online_base_dir)] == online_base_dir:        
                base_SFA_dir = GTSRB_SFA_dir_OnlineTest
                online_test = True
            else:
                base_SFA_dir = GTSRB_SFA_dir_training
                online_test = False 
    
            base_GTSRB_dir = "/local/escalafl/Alberto/GTSRB"
    
            sample_img_filename = "00000/00001_00000.ppm"
            fset = "02"
            for ii, image_filename in enumerate(iSeq.input_files):
                if online_test:
                    sfa_filename = GTSRB_SFA_dir_OnlineTest + "/SFA_" + fset + "/" + image_filename[-9:-3]+"txt"
                else:
                    sfa_filename = GTSRB_SFA_dir_training + "/SFA_" + fset + "/" + image_filename[-len(sample_img_filename):-3]+"txt"
                if ii==0:
                    print sfa_filename
                filed = open(sfa_filename, "wb")
                for i, xx in enumerate(sl[ii,0:number_SFA_features]):
                    if i==0:
                        filed.write('%f'%xx)
                    else:
                        filed.write('\n%f'%xx)
                filed.close( )
            
        
elif output_filename != None:
    fd = open(output_filename, "w")
    txt = ""
    for i, val in enumerate(results.typical_delta_newid):
        if i==0:
            txt="%f"%results.typical_delta_newid[i]
        else:
            txt += " %f"%results.typical_delta_newid[i]
    print "writing \"%s\" to; %s"%(txt, output_filename)
    fd.write(txt)
    fd.close()


if save_sorted_AE_Gauss_newid:
    error_Gauss_newid = numpy.abs(correct_labels_newid-regression_Gauss_newid)
    sorting_error_Gauss_newid = error_Gauss_newid.argsort()
    
    save_images_sorted_error_Gauss_newid_base_dir = "/local/tmp/escalafl/Alberto/saved_images_sorted_AE_Gauss_newid"
    print "saving images to directory:", save_images_sorted_error_Gauss_newid_base_dir
    decimate =  100
    for i, i_x in enumerate(sorting_error_Gauss_newid):
        x = subimages_newid[i_x]
        if i%decimate == 0:
            im_raw = numpy.reshape(x, (sNewid.subimage_width, sNewid.subimage_height)) #Remove ,3 for L
            if seq.convert_format in ["L", "RGB"]:
                im = scipy.misc.toimage(im_raw, mode=seq.convert_format)
            else:
                im = scipy.misc.toimage(im_raw, mode="L")

            fullname = os.path.join(save_images_sorted_error_Gauss_newid_base_dir, "image%05d_gt%+05f_e%+05f.png"%(i/decimate, correct_labels_newid[i_x], regression_Gauss_newid[i_x]))
            im.save(fullname)
    total_samples = len(sorting_error_Gauss_newid)
    worst_samples_nr = min(150, total_samples)
    for i in range(worst_samples_nr):
        i_x = sorting_error_Gauss_newid[total_samples - i - 1]
        x = subimages_newid[i_x]
        if seq.convert_format == "L":
            im_raw = numpy.reshape(x, (sNewid.subimage_width, sNewid.subimage_height)) #Remove ,3 for L
            im = scipy.misc.toimage(im_raw, mode=seq.convert_format)
        elif seq.convert_format == "RGB":
            im_raw = numpy.reshape(x, (sNewid.subimage_width, sNewid.subimage_height, 3)) #Remove ,3 for L
            im = scipy.misc.toimage(im_raw, mode=seq.convert_format)
        else:
            im = scipy.misc.toimage(im_raw, mode="L")

        fullname = os.path.join(save_images_sorted_error_Gauss_newid_base_dir, "image_worst%05d_gt%+05f_e%+05f.png"%(i, correct_labels_newid[i_x], regression_Gauss_newid[i_x]))
        im.save(fullname)


if save_sorted_incorrect_class_Gauss_newid:
    d1 = numpy.array(correct_classes_newid, dtype="int")
    d2 = numpy.array(classes_Gauss_newid, dtype="int")
    
    incorrect_Gauss_newid = (d1==d2)
    sorting_incorrect_Gauss_newid = incorrect_Gauss_newid.argsort()
    
    save_images_sorted_incorrect_class_Gauss_newid_base_dir = "/local/tmp/escalafl/Alberto/saved_images_sorted_incorrect_class_Gauss_newid"
    print "saving images to directory:", save_images_sorted_incorrect_class_Gauss_newid_base_dir
    decimate =  1
    for i, i_x in enumerate(sorting_incorrect_Gauss_newid):
        x = subimages_newid[i_x]
        if i%decimate == 0:
            if seq.convert_format == "L":
                im_raw = numpy.reshape(x, (sNewid.subimage_width, sNewid.subimage_height))
                im = scipy.misc.toimage(im_raw, mode=seq.convert_format)
            elif seq.convert_format == "RGB":
                im_raw = numpy.reshape(x, (sNewid.subimage_width, sNewid.subimage_height, 3))
                im = scipy.misc.toimage(im_raw, mode=seq.convert_format)
            else:
                im = scipy.misc.toimage(im_raw, mode="L")

            fullname = os.path.join(save_images_sorted_incorrect_class_Gauss_newid_base_dir, "image%05d_gt%03d_c%03d.png"%(i/decimate, correct_classes_newid[i_x], classes_Gauss_newid[i_x]))
            im.save(fullname)

#Save training, known_id, and new_id data in the format of libsvm
if export_data_to_libsvm:
    this_time = int(time.time())
    print "Saving output features in the format of libsvm (all components included). Timestamp:", this_time
    more_nodes.export_to_libsvm(correct_classes_training, sl_seq_training, "libsvm_data/training2%011d"%this_time)
    more_nodes.export_to_libsvm(correct_classes_seenid, sl_seq_seenid, "libsvm_data/seenid2%011d"%this_time)
    more_nodes.export_to_libsvm(correct_classes_newid, sl_seq_newid, "libsvm_data/newid2%011d"%this_time)

compute_background_detection = True #and False
cutoff_backgrounds = [0.975, 0.98, 0.985, 0.99, 0.995, 0.998, 0.999, 0.9995, 0.99995]
if compute_background_detection and Parameters == experiment_datasets.ParamsRFaceCentering:
    print "false_background should be as small as possible <= 0.01, correct_background should be large >= 0.8"
    for cutoff_background in cutoff_backgrounds:
        print "for cutoff_background = %f"%cutoff_background
        for seq, regression in [(iTrain,regression_Gauss_training), (iSeenid,regression_Gauss_seenid), (iNewid,regression_Gauss_newid)]: 
            bs = seq.block_size
            correct_background = (regression[-bs:]>cutoff_background).sum() * 1.0 / bs
            false_background = (regression[0:-bs]>cutoff_background).sum() * 1.0 / len(regression[0:-bs])
            print "correct_background = ", correct_background, "false_background =", false_background 


if minutes_sleep < 0:
    lock.acquire()
    q = open(cuicuilco_queue, "r")
    next_pid = q.readline()
    print "queue_top was: ", next_pid, "we are:", pid,
    queue_rest = q.readlines()
    print "queue_rest=", queue_rest
    served = True
    q.close()

    print "removing us from the queue"
    q2 = open(cuicuilco_queue, "w")
    for line in queue_rest:
        q2.write(line)
    q2.close()
    lock.release()




if enable_display:
    print "Creating GUI..."
    
    print "****** Displaying Typical Images used for Training and Testing **********"
    tmp_fig = plt.figure()
    plt.suptitle(Parameters.name + ". Image Datasets")
     
    num_images_per_set = 4 
    
    subimages_training = subimages
    num_images_training
    
    sequences = [subimages_training, subimages_seenid, subimages_newid]
    messages = ["Training Images", "Seen Id Images", "New Id Images"]
    nums_images = [num_images_training, num_images_seenid, num_images_newid]
    #Warning, next is for L, then for RGB
    #sizes = [(sTrain.subimage_height, sTrain.subimage_width), (sSeenid.subimage_height, sSeenid.subimage_width), \
    #         (sNewid.subimage_height, sNewid.subimage_width)]
    #Note: sizes should be in practice the same, no need to generalize
    sizes = [subimage_shape, subimage_shape, subimage_shape]
    
    for seqn in range(3):
        for im in range(num_images_per_set):
            tmp_sb = plt.subplot(3, num_images_per_set, num_images_per_set*seqn + im+1)
            y = im * (nums_images[seqn]-1) / (num_images_per_set - 1)
#            print sequences[seqn][y].shape
#            print sizes[seqn]         
            subimage_im = sequences[seqn][y].reshape(sizes[seqn])
                
            tmp_sb.imshow(subimage_im.clip(0,max_clip), norm=None, vmin=0, vmax=max_clip, aspect='auto', interpolation='nearest', origin='upper', cmap=mpl.pyplot.cm.gray)
    #        subimage_im = subimage_im/256.0
    #        tmp_sb.imshow(subimage_im.clip(0,1), origin='upper')
            if im == 0:
                plt.ylabel(messages[seqn])
            else:
                tmp_sb.axis('off')
    
    
    print "************ Displaying SFA Output Signals **************"
    #Create Figure
    f0 = plt.figure()
    plt.suptitle(Parameters.name + ". Slow Signals")
      
    #display SFA of Training Set
    p11 = plt.subplot(1,3,1)
    plt.title("Output Signals (Training Set)")
    sl_seqdisp = sl_seq_training[:, range(0,hierarchy_out_dim)]
    sl_seqdisp = scale_to(sl_seqdisp, sl_seq_training.mean(axis=0), sl_seq_training.max(axis=0)-sl_seq_training.min(axis=0), 127.5, 255.0, scale_disp, 'tanh')
    p11.imshow(sl_seqdisp.clip(0,255), aspect='auto', interpolation='nearest', origin='upper', cmap=mpl.pyplot.cm.gray)
    plt.xlabel("min[0]=%.3f, max[0]=%.3f, scale=%.3f\n e[]=" % (sl_seq_training.min(axis=0)[0], sl_seq_training.max(axis=0)[0], scale_disp)+str3(sfa_libs.comp_eta(sl_seq_training)[0:5]))
    plt.ylabel("Training Images")
    
    #display SFA of Known Id testing Set
    p12 = plt.subplot(1,3,2)
    plt.title("Output Signals (Seen Id Test Set)")
    sl_seqdisp = sl_seq_seenid[:, range(0,hierarchy_out_dim)]
    sl_seqdisp = scale_to(sl_seqdisp, sl_seq_training.mean(axis=0), sl_seq_training.max(axis=0)-sl_seq_training.min(axis=0), 127.5, 255.0, scale_disp, 'tanh')
    p12.imshow(sl_seqdisp.clip(0,255), aspect='auto', interpolation='nearest', origin='upper', cmap=mpl.pyplot.cm.gray)
    plt.xlabel("min[0]=%.3f, max[0]=%.3f, scale=%.3f\n e[]=" % (sl_seq_seenid.min(axis=0)[0], sl_seq_seenid.max(axis=0)[0], scale_disp)+str3(sfa_libs.comp_eta(sl_seq_seenid)[0:5]))
    plt.ylabel("Seen Id Images")
    
    #display SFA of Known Id testing Set
    p13 = plt.subplot(1,3,3)
    plt.title("Output Signals (New Id Test Set)")
    sl_seqdisp = sl_seq_newid[:, range(0,hierarchy_out_dim)]
    sl_seqdisp = scale_to(sl_seqdisp, sl_seq_training.mean(axis=0), sl_seq_training.max(axis=0)-sl_seq_training.min(axis=0), 127.5, 255.0, scale_disp, 'tanh')
    p13.imshow(sl_seqdisp.clip(0,255), aspect='auto', interpolation='nearest', origin='upper', cmap=mpl.pyplot.cm.gray)
    plt.xlabel("min[0]=%.3f, max[0]=%.3f, scale=%.3f\n e[]=" % (sl_seq_newid.min(axis=0)[0], sl_seq_newid.max(axis=0)[0], scale_disp)+str3(sfa_libs.comp_eta(sl_seq_newid)[0:5]))
    plt.ylabel("New Id Images")
    
    
    relevant_out_dim = 3
    if hierarchy_out_dim < relevant_out_dim:
        relevant_out_dim = hierarchy_out_dim
    
    print "************ Plotting Relevant SFA Output Signals **************"
    ax_5 = plt.figure()
    ax_5.subplots_adjust(hspace=0.5)
    plt.suptitle(Parameters.name + ". Most Relevant Slow Signals")
    
    sp11 = plt.subplot(2,2,1)
    plt.title("SFA Outputs. (Training Set)")
     
    relevant_sfa_indices = numpy.arange(relevant_out_dim)
    reversed_sfa_indices = range(relevant_out_dim)
    reversed_sfa_indices.reverse()
    
    r_color = (1-relevant_sfa_indices * 1.0 / relevant_out_dim) * 0.8 + 0.2
    g_color = (relevant_sfa_indices * 1.0 / relevant_out_dim) * 0.8 + 0.2
    #r_color = (0.5*numpy.cos(relevant_sfa_indices * numpy.pi / relevant_out_dim) + 0.5).clip(0.0,1.0)
    #g_color = (0.5*numpy.cos(relevant_sfa_indices * numpy.pi / relevant_out_dim + numpy.pi)+0.5).clip(0.0,1.0)
    b_color = relevant_sfa_indices * 0.0
    r_color = [1.0, 0.0, 0.0]
    g_color = [28/255.0, 251/255.0, 55/255.0]
    b_color = [33/255.0, 79/255.0, 196/255.0]  
    max_amplitude_sfa = 3.0 # 2.0
    
    sfa_text_labels = ["Slowest Signal", "2nd Slowest Signal", "3rd Slowest Signal"]
    
    print num_images_training, sl_seq_training.shape
    for sig in reversed_sfa_indices:
        plt.plot(numpy.arange(num_images_training), sl_seq_training[:, sig], ".", color=(r_color[sig], g_color[sig], b_color[sig]), label=sfa_text_labels[sig], markersize=6, markerfacecolor=(r_color[sig], g_color[sig], b_color[sig]))
    #    plt.plot(numpy.arange(num_images_training), sl_seq_training[:, sig], ".")
    plt.ylim(-max_amplitude_sfa, max_amplitude_sfa)
    plt.xlim(0, num_images_training)
    plt.xlabel("Input Image, Training Set ")
    plt.ylabel("Slow Signals")
    
    sp12 = plt.subplot(2,2,2)
    if Parameters.train_mode == 'serial' or Parameters.train_mode == 'mixed' :
        plt.title("Example of Ideal SFA Outputs")
        num_blocks = num_images_training/block_size
        sl_optimal = numpy.zeros((num_images, relevant_out_dim))
        factor = -1.0 * numpy.sqrt(2.0)
        t_opt=numpy.linspace(0, numpy.pi, num_blocks)
        for sig in range(relevant_out_dim):
            sl_optimal[:,sig] = wider_1Darray(factor * numpy.cos((sig+1) * t_opt), block_size)
        
        for sig in reversed_sfa_indices:
            colour = sig * 0.6 / relevant_out_dim 
            plt.plot(numpy.arange(num_images_training), sl_optimal[:, sig], ".", color=(r_color[sig], g_color[sig], b_color[sig]), label=sfa_text_labels[sig], markersize=6, markerfacecolor=(r_color[sig], g_color[sig], b_color[sig]))
        plt.ylim(-max_amplitude_sfa, max_amplitude_sfa)
        plt.xlim(0, num_images_training)
        plt.xlabel("Input Image, Training Set ")
        plt.ylabel("Slow Signals")
    else:
        plt.title("Example Ideal SFA Outputs Not Available")
    
    sp13 = plt.subplot(2,2,3)
    plt.title("SFA Outputs. (Seen Id Test Set)")
    for sig in reversed_sfa_indices:
        colour = sig * 1.0 /relevant_out_dim 
    #    Warning!!!
        plt.plot(numpy.arange(num_images_seenid), sl_seq_seenid[:, sig], ".", color=(r_color[sig], g_color[sig], b_color[sig]), label=sfa_text_labels[sig], markersize=6, markerfacecolor=(r_color[sig], g_color[sig], b_color[sig]))
    #    plt.plot(numpy.arange(len(subimages)), subimages[:, sig], ".", color=(r_color[sig], g_color[sig], b_color[sig]), label=sfa_text_labels[sig], markersize=6, markerfacecolor=(r_color[sig], g_color[sig], b_color[sig]))
    plt.ylim(-max_amplitude_sfa, max_amplitude_sfa)
    plt.xlim(0, num_images_seenid)
    #plt.ylim(0, 1)
    plt.xlabel("Input Image, Seen Id Test")
    plt.ylabel("Slow Signals")
    #plt.legend( (sfa_text_labels[2], sfa_text_labels[1], sfa_text_labels[0]), loc=4)
    
    sp14 = plt.subplot(2,2,4)
    plt.title("SFA Outputs. (New Id Test Set)")
    for sig in reversed_sfa_indices:
        colour = sig * 1.0 /relevant_out_dim 
        plt.plot(numpy.arange(num_images_newid), sl_seq_newid[:, sig], ".", color=(r_color[sig], g_color[sig], b_color[sig]), label=sfa_text_labels[sig], markersize=6, markerfacecolor=(r_color[sig], g_color[sig], b_color[sig]))
    plt.ylim(-max_amplitude_sfa, max_amplitude_sfa)
    plt.xlim(0, num_images_newid)
    plt.xlabel("Input Image, New Id Test")
    plt.ylabel("Slow Signals")
    
    show_linear_inv    = True
    show_linear_masks  = True
    show_linear_masks_ext  = True
    show_linear_morphs = True
    show_localized_masks  = True
    show_localized_morphs = True
    show_progressive_morph = False
    
    show_translation_x = False
    
    print "************ Displaying Training Set SFA and Inverses **************"
    #Create Figure
    f1 = plt.figure()
    ax_5.subplots_adjust(hspace=0.5)
    plt.suptitle(Network.name)
      
    #display SFA
    f1a11 = plt.subplot(2,3,1)
    plt.title("Output Unit (Top Node)")
    sl_seqdisp = sl_seq[:, range(0,hierarchy_out_dim)]
    sl_seqdisp = scale_to(sl_seqdisp, sl_seq.mean(), sl_seq.max()-sl_seq.min(), 127.5, 255.0, scale_disp, 'tanh')
    f1a11.imshow(sl_seqdisp.clip(0,255), aspect='auto', interpolation='nearest', origin='upper', cmap=mpl.pyplot.cm.gray)
    plt.xlabel("min=%.3f, max=%.3f, scale=%.3f\n e[]=" % (sl_seq.min(), sl_seq.max(), scale_disp)+str3(sfa_libs.comp_eta(sl_seq)[0:5]))
    
    #display first image
    #Alternative: im1.show(command="xv")
    f1a12 = plt.subplot(2,3,2)
    plt.title("A particular image in the sequence")
    #im_smalldisp = im_small.copy()
    #f1a12.imshow(im_smalldisp, aspect='auto', interpolation='nearest', origin='upper', cmap=mpl.pyplot.cm.gray)
    f1a13 = plt.subplot(2,3,3)
    plt.title("Reconstructed Image")
        
    f1a21 = plt.subplot(2,3,4)
    plt.title("Reconstruction Error")
        
    f1a22 = plt.subplot(2,3,5)
    plt.title("DIfferential Reconstruction y_pinv_(t+1) - y_pinv_(t)")
        
    f1a23 = plt.subplot(2,3,6)
    plt.title("Pseudoinverse of 0 / PINV(y) - PINV(0)")
    if show_linear_inv == True:
        sfa_zero = numpy.zeros((1, hierarchy_out_dim))
        pinv_zero = flow.inverse(sfa_zero)
    #WARNING L and RGB
    #    pinv_zero = pinv_zero.reshape((sTrain.subimage_height, sTrain.subimage_width))
        pinv_zero = pinv_zero.reshape(subimage_shape)
    
        error_scale_disp=1.5
    #WARNING L and RGB
        pinv_zero_disp = scale_to(pinv_zero, pinv_zero.mean(), pinv_zero.max()-pinv_zero.min(), max_clip/2.0, max_clip, error_scale_disp, 'tanh')
    #    pinv_zero_disp = scale_to(pinv_zero/256.0, pinv_zero.mean()/256.0, pinv_zero.max()/256.0-pinv_zero.min()/256.0, 0.5, 1.0, error_scale_disp, 'tanh')
        f1a23.set_xlabel("min=%.2f, max=%.2f, std=%.2f, scale=%.2f, zero" % (pinv_zero_disp.min(), pinv_zero_disp.max(), pinv_zero_disp.std(), error_scale_disp))
    #WARNING L and RGB
    #    f1a23.imshow(pinv_zero_disp.clip(0,255), aspect='auto', interpolation='nearest', origin='upper', cmap=mpl.pyplot.cm.gray)
        f1a23.imshow(pinv_zero_disp.clip(0,max_clip), aspect='auto', interpolation='nearest', origin='upper', cmap=mpl.pyplot.cm.gray)
    else:
        pinv_zero = None
    
    #Retrieve Image in Sequence
    def on_press_inv(event):
        global plt, f1, f1a12, f1a13, f1a21, f1a22, fla23, subimages, L2, sTrain, sl_seq, pinv_zero, flow, error_scale_disp
        print 'you pressed', event.button, event.xdata, event.ydata
        y = int(event.ydata)
        if y < 0:
            y = 0
        if y >= num_images:
            y = num_images -1
        print "y=" + str(y)
    
    #Display Original Image
    #WARNING L and RGB
    #    subimage_im = subimages[y].reshape((sTrain.subimage_height, sTrain.subimage_width)) + 0.0
        subimage_im = subimages[y].reshape(subimage_shape) + 0.0
        
        if show_translation_x:
            if sTrain.trans_sampled:
                subimage_im[:, sTrain.subimage_width/2.0-sTrain.translations_x[y]] = max_clip
                subimage_im[:, sTrain.subimage_width/2.0-regression_Gauss_training[y]/reduction_factor] = 0
            else:
                subimage_im[:, sTrain.subimage_width/2.0-sTrain.translations_x[y]*sTrain.pixelsampling_x] = max_clip
                subimage_im[:, sTrain.subimage_width/2.0-regression_Gauss_training[y]/reduction_factor*sTrain.pixelsampling_x] = 0
        
        f1a12.imshow(subimage_im.clip(0,max_clip), aspect='auto', interpolation='nearest', origin='upper', cmap=mpl.pyplot.cm.gray)
    
        if show_linear_inv == False:
            f1.canvas.draw()
            return
    
    
    #Display Reconstructed Image
        data_out = sl_seq[y].reshape((1, hierarchy_out_dim))
        inverted_im = flow.inverse(data_out)
        inverted_im = inverted_im.reshape(subimage_shape)
        f1a13.imshow(inverted_im.clip(0,max_clip), aspect='auto', interpolation='nearest', origin='upper', cmap=mpl.pyplot.cm.gray)        
        
    #Display Reconstruction Error
        error_scale_disp=1.5
        error_im = subimages[y].reshape(subimage_shape) - inverted_im 
        error_im_disp = scale_to(error_im, error_im.mean(), error_im.max()-error_im.min(), max_clip/2.0, max_clip, error_scale_disp, 'tanh')
        f1a21.imshow(error_im_disp.clip(0,max_clip), aspect='auto', interpolation='nearest', origin='upper', cmap=mpl.pyplot.cm.gray)       
        plt.axis = f1a21
        f1a21.set_xlabel("min=%.2f, max=%.2f, std=%.2f, scale=%.2f, y=%d" % (error_im.min(), error_im.max(), error_im.std(), error_scale_disp, y))
    #Display Differencial change in reconstruction
        error_scale_disp=1.5
        if y >= sTrain.num_images - 1:
            y_next = 0
        else:
            y_next = y+1
        print "y_next=" + str(y_next)
        data_out2 = sl_seq[y_next].reshape((1, hierarchy_out_dim))
        inverted_im2 = flow.inverse(data_out2).reshape(subimage_shape)
        diff_im = inverted_im2 - inverted_im 
        diff_im_disp = scale_to(diff_im, diff_im.mean(), diff_im.max()-diff_im.min(), max_clip/2.0, max_clip, error_scale_disp, 'tanh')
        f1a22.imshow(diff_im_disp.clip(0,max_clip), aspect='auto', interpolation='nearest', origin='upper', cmap=mpl.pyplot.cm.gray)       
        plt.axis = f1a22
        f1a22.set_xlabel("min=%.2f, max=%.2f, std=%.2f, scale=%.2f, y=%d" % (diff_im.min(), diff_im.max(), diff_im.std(), error_scale_disp, y))
    #Display Difference from PINV(y) and PINV(0)
        error_scale_disp=1.0
        dif_pinv = inverted_im - pinv_zero 
        dif_pinv_disp = scale_to(dif_pinv, dif_pinv.mean(), dif_pinv.max()-dif_pinv.min(), max_clip/2.0, max_clip, error_scale_disp, 'tanh')
        f1a23.imshow(dif_pinv_disp.clip(0,max_clip), aspect='auto', interpolation='nearest', origin='upper', cmap=mpl.pyplot.cm.gray)       
        plt.axis = f1a23
        f1a23.set_xlabel("PINV(y) - PINV(0): min=%.2f, max=%.2f, std=%.2f, scale=%.2f, y=%d" % (dif_pinv.min(), dif_pinv.max(), dif_pinv.std(), error_scale_disp, y))
        
        f1.canvas.draw()
        
    f1.canvas.mpl_connect('button_press_event', on_press_inv)
        
    
    print "************ Displaying Test Set SFA and Inverses through kNN from Seen Id data **************"
    #TODO:Make this a parameter!
    kNN_k = 30
    #Create Figure
    fkNNinv = plt.figure()
    ax_5.subplots_adjust(hspace=0.5)
    plt.suptitle(Network.name+"Reconstruction using kNN (+ avg) from output features. k="+str(kNN_k))
      
    #display SFA
    f_kNNinv_a11 = plt.subplot(2,4,1)
    plt.title("Output Unit (Top Node) New Id")
    sl_seqdisp = sl_seq_newid[:, range(0,hierarchy_out_dim)]
    sl_seqdisp = scale_to(sl_seqdisp, sl_seq_newid.mean(), sl_seq_newid.max()-sl_seq_newid.min(), 127.5, 255.0, scale_disp, 'tanh')
    f_kNNinv_a11.imshow(sl_seqdisp.clip(0,255), aspect='auto', interpolation='nearest', origin='upper', cmap=mpl.pyplot.cm.gray)
    plt.xlabel("min=%.3f, max=%.3f, scale=%.3f\n e[]=" % (sl_seq.min(), sl_seq.max(), scale_disp)+str3(sfa_libs.comp_eta(sl_seq)[0:5]))
    
    #display first image
    #Alternative: im1.show(command="xv")
    f_kNNinv_a12 = plt.subplot(2,4,2)
    plt.title("A particular image in the sequence")
    #im_smalldisp = im_small.copy()
    #f_kNNinv_a12.imshow(im_smalldisp, aspect='auto', interpolation='nearest', origin='upper', cmap=mpl.pyplot.cm.gray)
    f_kNNinv_a13 = plt.subplot(2,4,3)
    plt.title("Reconstructed Image using kNN")

    if estimate_explained_var_linear_global_N == -1:
        training_data_lmodel = subimages_seenid
        features_lmodel = sl_seq_seenid[:,0:num_features_linear_model]
        indices_all_train_lmodel = more_nodes.random_subindices(training_data_lmodel.shape[0], number_samples_EV_linear_global)
        indices_all_newid = numpy.arange(subimages_newid.shape[0]) #Select all images of newid
         
        lr_node = mdp.nodes.LinearRegressionNode()
        sl_seq_training_sel = features_lmodel[indices_all_train_lmodel, :]
        subimages_train_sel = training_data_lmodel[indices_all_train_lmodel]
        lr_node.train(sl_seq_training_sel, subimages_train_sel) #Notice that the input "x"=n_sfa_x and the output to learn is "y" = x_pca
        lr_node.stop_training()  
      
        sl_seq_newid_sel = sl_seq_newid[indices_all_newid, 0:num_features_linear_model]
        subimages_newid_app = lr_node.execute(sl_seq_newid_sel)  
    else:
        subimages_newid_app = subimages_newid
        
    f_kNNinv_a14 = plt.subplot(2,4,4)
    if estimate_explained_var_linear_global_N == -1:
        plt.title("Linearly Reconstrion. #F=%d"%num_features_linear_model)
    else:
        plt.title("Linearly Reconstrion NOT Enabled. #F=%d"%num_features_linear_model)
        
    f_kNNinv_a21 = plt.subplot(2,4,5)
    plt.title("Reconstruction Error, k=1")

    f_kNNinv_a22 = plt.subplot(2,4,6)
    plt.title("Reconstructed Image using kNN, k=1")
            
    f_kNNinv_a23 = plt.subplot(2,4,7)
    plt.title("kNN Reconstruction Error")
          
    f_kNNinv_a24 = plt.subplot(2,4,8)
    plt.title("Linear Reconstruction Error")

    #Retrieve Image in Sequence
    def on_press_kNN(event):
        #Why is this declared global??? 
        global plt, f_kNNinv_a12, f_kNNinv_a13, f_kNNinv_a14, f_kNNinv_a21, f_kNNinv_a22, f_kNNinv_a23, f_kNNinv_a24, subimages_seenid, subimages_newid, sl_seq_seenid, sl_seq_newid, subimages_newid_app, error_scale_disp
        print 'you pressed', event.button, event.xdata, event.ydata
        y = int(event.ydata)
        if y < 0:
            y = 0
        if y >= num_images_newid:
            y = num_images_newid -1
        print "y=" + str(y)
    
    #Display Original Image
    #WARNING L and RGB
    #    subimage_im = subimages[y].reshape((sTrain.subimage_height, sTrain.subimage_width)) + 0.0
        subimage_im = subimages_newid[y].reshape(subimage_shape) + 0.0              
        f_kNNinv_a12.imshow(subimage_im.clip(0,max_clip), aspect='auto', interpolation='nearest', origin='upper', cmap=mpl.pyplot.cm.gray)      
        f_kNNinv_a12.set_xlabel("Selected image y=%d"%y)
      
    #Display Reconstructed Image kNN
        data_out = sl_seq_newid[y].reshape((1, hierarchy_out_dim))
        x_app_test = more_nodes.approximate_kNN_op(subimages_seenid, sl_seq_seenid, data_out, k=kNN_k, ignore_closest_match=True, operation="average")
        inverted_im_kNNavg = x_app_test.reshape(subimage_shape)        
        f_kNNinv_a13.imshow(inverted_im_kNNavg.clip(0,max_clip), aspect='auto', interpolation='nearest', origin='upper', cmap=mpl.pyplot.cm.gray)        
    
    #Display Linearly Reconstructed Image
        data_out = sl_seq_newid[y].reshape((1, hierarchy_out_dim))
        x_app_test = subimages_newid_app[y]
        inverted_im_LRec = x_app_test.reshape(subimage_shape)        
        f_kNNinv_a14.imshow(inverted_im_LRec.clip(0,max_clip), aspect='auto', interpolation='nearest', origin='upper', cmap=mpl.pyplot.cm.gray)        
        
    #Display Reconstructed Image for kNN_k=1
        data_out = sl_seq_newid[y].reshape((1, hierarchy_out_dim))
        x_app_test = more_nodes.approximate_kNN_op(subimages_seenid, sl_seq_seenid, data_out, k=1, ignore_closest_match=False, operation="average")
        inverted_im_kNN1 = x_app_test.reshape(subimage_shape)        
        f_kNNinv_a22.imshow(inverted_im_kNN1.clip(0,max_clip), aspect='auto', interpolation='nearest', origin='upper', cmap=mpl.pyplot.cm.gray)        

    #Display Reconstruction Error, kNN1
        error_scale_disp=1.5
        error_im = subimage_im - inverted_im_kNN1 
        error_im_disp = scale_to(error_im, error_im.mean(), error_im.max()-error_im.min(), max_clip/2.0, max_clip, error_scale_disp, 'tanh')
        f_kNNinv_a21.imshow(error_im_disp.clip(0,max_clip), aspect='auto', interpolation='nearest', origin='upper', cmap=mpl.pyplot.cm.gray)       
        plt.axis = f_kNNinv_a21
        f_kNNinv_a21.set_xlabel("min=%.2f, max=%.2f, std=%.2f, scale=%.2f" % (error_im.min(), error_im.max(), error_im.std(), error_scale_disp))

    #Display Reconstruction Error, kNN average
        error_scale_disp=1.5
        error_im = subimage_im - inverted_im_kNNavg
        error_im_disp = scale_to(error_im, error_im.mean(), error_im.max()-error_im.min(), max_clip/2.0, max_clip, error_scale_disp, 'tanh')
        f_kNNinv_a23.imshow(error_im_disp.clip(0,max_clip), aspect='auto', interpolation='nearest', origin='upper', cmap=mpl.pyplot.cm.gray)       
        plt.axis = f_kNNinv_a23
        f_kNNinv_a23.set_xlabel("min=%.2f, max=%.2f, std=%.2f, scale=%.2f" % (error_im.min(), error_im.max(), error_im.std(), error_scale_disp))

    #Display Linear Reconstruction Error
        error_scale_disp=1.5
        error_im = subimage_im - inverted_im_LRec
        error_im_disp = scale_to(error_im, error_im.mean(), error_im.max()-error_im.min(), max_clip/2.0, max_clip, error_scale_disp, 'tanh')
        f_kNNinv_a24.imshow(error_im_disp.clip(0,max_clip), aspect='auto', interpolation='nearest', origin='upper', cmap=mpl.pyplot.cm.gray)       
        plt.axis = f_kNNinv_a24
        f_kNNinv_a24.set_xlabel("min=%.2f, max=%.2f, std=%.2f, scale=%.2f" % (error_im.min(), error_im.max(), error_im.std(), error_scale_disp))
    
        
        fkNNinv.canvas.draw()
        
    fkNNinv.canvas.mpl_connect('button_press_event', on_press_kNN)
    
    
    
    
    
    print "************ Displaying Classification / Regression Results **************"
    #Create Figure
    f2 = plt.figure()
    plt.suptitle("Classification Results (Class Numbers)  using %d Slow Signals"%reg_num_signals)
    #plt.title("Training Set")
    p11 = f2.add_subplot(311, frame_on=False)
    xlabel="Image Number, Training Set."
    p11.plot(numpy.arange(len(correct_classes_training)), correct_classes_training, 'r.', markersize=2, markerfacecolor='red')
    if enable_ncc_cfr:
        p11.plot(numpy.arange(len(classes_ncc_training)), classes_ncc_training, 'k.', markersize=2, markerfacecolor='black')
        xlabel += " CR_ncc=%.3f,"%results.class_ncc_rate_train
    if enable_kNN_cfr:
        p11.plot(numpy.arange(len(classes_kNN_training)), classes_kNN_training, 'b.', markersize=2, markerfacecolor='blue')
        xlabel += " CR_kNN=%.3f,"%results.class_kNN_rate_train
    p11.plot(numpy.arange(len(classes_Gauss_training)), classes_Gauss_training, 'm.', markersize=2, markerfacecolor='magenta')
    xlabel += " CR_Gauss=%.3f,"%results.class_Gauss_rate_train
    if enable_svm_cfr:
        p11.plot(numpy.arange(len(classes_svm_training)), classes_svm_training, 'g.', markersize=2, markerfacecolor='green')
        xlabel += " CR_SVM=%.3f,"%results.class_svm_rate_train
    plt.xlabel(xlabel)
    plt.ylabel("Class Number")
    p11.grid(True)
    #draw horizontal and vertical lines
    #majorLocator_x   = MultipleLocator(block_size)
    #majorLocator_y   = MultipleLocator(1)
    #p11.xaxis.set_major_locator(majorLocator_x)
    ##p11.yaxis.set_major_locator(majorLocator_y)
    #plt.xticks(numpy.arange(0, len(labels_kNN_training), block_size)) 
    #plt.yticks(numpy.arange(0, len(labels_kNN_training), block_size)) 
    #print "Block_size is: ", block_size
    
    p12 = f2.add_subplot(312, frame_on=False)
    xlabel="Image Number, Seen Id Set."
    p12.plot(numpy.arange(len(correct_classes_seenid)), correct_classes_seenid, 'r.', markersize=2, markerfacecolor='red')
    if enable_ncc_cfr:
        p12.plot(numpy.arange(len(classes_ncc_seenid)), classes_ncc_seenid, 'k.', markersize=2, markerfacecolor='black')
        xlabel += " CR_ncc=%.3f,"%results.class_ncc_rate_seenid
    if enable_kNN_cfr:
        p12.plot(numpy.arange(len(classes_kNN_seenid)), classes_kNN_seenid, 'b.', markersize=2, markerfacecolor='blue')
        xlabel += " CR_kNN=%.3f,"%results.class_kNN_rate_seenid
    p12.plot(numpy.arange(len(classes_Gauss_seenid)), classes_Gauss_seenid, 'm.', markersize=2, markerfacecolor='magenta')
    xlabel += " CR_Gauss=%.3f,"%results.class_Gauss_rate_seenid
    if enable_svm_cfr:
        p12.plot(numpy.arange(len(classes_kNN_seenid)), classes_svm_seenid, 'g.', markersize=2, markerfacecolor='green')
        xlabel += " CR_SVM=%.3f,"%results.class_svm_rate_seenid
    plt.xlabel(xlabel)
    plt.ylabel("Class Number")
    p12.grid(True)
    #p12.plot(numpy.arange(len(labels_ccc_seenid)), correct_classes_seenid, 'mo', markersize=3, markerfacecolor='magenta')
    #majorLocator_y   = MultipleLocator(block_size)
    ##majorLocator_x   = MultipleLocator(block_size_seenid)
    #majorLocator_x   = MultipleLocator(block_size_seenid)
    #p12.xaxis.set_major_locator(majorLocator_x)
    #p12.yaxis.set_major_locator(majorLocator_y)
    #majorLocator_y   = MultipleLocator(block_size)
    
    p13 = f2.add_subplot(313, frame_on=False)
    xlabel="Image Number, New Id Set."
    p13.plot(numpy.arange(len(correct_classes_newid)), correct_classes_newid, 'r.', markersize=2, markerfacecolor='red')
    if enable_ncc_cfr:
        p13.plot(numpy.arange(len(classes_ncc_newid)), classes_ncc_newid, 'k.', markersize=2, markerfacecolor='black')
        xlabel += " CR_ncc=%.3f,"%results.class_ncc_rate_newid
    if enable_kNN_cfr:
        p13.plot(numpy.arange(len(classes_kNN_newid)), classes_kNN_newid, 'b.', markersize=2, markerfacecolor='blue')
        xlabel += " CR_kNN=%.3f,"%results.class_kNN_rate_newid
    p13.plot(numpy.arange(len(classes_Gauss_newid)), classes_Gauss_newid, 'm.', markersize=2, markerfacecolor='magenta')
    xlabel += " CR_Gauss=%.3f,"%results.class_Gauss_rate_newid
    if enable_svm_cfr:
        p13.plot(numpy.arange(len(classes_svm_newid)), classes_svm_newid, 'g.', markersize=2, markerfacecolor='green')
        xlabel += " CR_svm=%.3f,"%results.class_svm_rate_newid
    plt.xlabel(xlabel)
    plt.ylabel("Class Number")
    p13.grid(True)
    #majorLocator_y = MultipleLocator(block_size)
    ##majorLocator_x   = MultipleLocator(block_size_seenid)
    #majorLocator_x   = MultipleLocator(block_size_newid)
    #p13.xaxis.set_major_locator(majorLocator_x)
    ##p13.yaxis.set_major_locator(majorLocator_y)
    
    f3 = plt.figure()
      
    plt.suptitle("Regression Results (Labels) using %d Slow Signals"%reg_num_signals)
    #plt.title("Training Set")
    p11 = f3.add_subplot(311, frame_on=False)
    #correct_classes_training = numpy.arange(len(labels_ccc_training)) / block_size
    xlabel="Image Number, Training Set."
    regression_text_labels = []
    if enable_ncc_cfr:
        p11.plot(numpy.arange(len(labels_ncc_training)), labels_ncc_training, 'k.', markersize=3, markerfacecolor='black')
        xlabel += " MSE_ncc=%f,"%(results.mse_ncc_train)
        regression_text_labels.append("Nearest Centroid Class.")
    if enable_kNN_cfr:
        p11.plot(numpy.arange(len(labels_kNN_training)), labels_kNN_training, 'b.', markersize=3, markerfacecolor='blue')
        xlabel += " MSE_kNN=%f,"%(results.mse_kNN_train)
        regression_text_labels.append("kNN")
    if enable_svm_cfr:
        p11.plot(numpy.arange(len(regression_svm_training)), regression_svm_training, 'g.', markersize=3, markerfacecolor='green')
        xlabel += " MSE_svm=%f,"%(results.mse_svm_train)
        regression_text_labels.append("SVM")
    if enable_gc_cfr:
        p11.plot(numpy.arange(len(regression_Gauss_training)), regression_Gauss_training, 'm.', markersize=3, markerfacecolor='magenta')
        xlabel += " MSE_Gauss=%f,"%(results.mse_gauss_train)        
        regression_text_labels.append("Gaussian Class/Regr.")   
    if enable_lr_cfr:
#        p11.plot(numpy.arange(len(correct_labels_training)), regression_lr_training, 'b.', markersize=3, markerfacecolor='blue') 
        p11.plot(numpy.arange(len(correct_labels_training)), regression_lr_training, 'c.', markersize=3, markerfacecolor='cyan') 
        xlabel += " MSE_lr=%f,"%(results.mse_lr_train)
        regression_text_labels.append("LR")

    p11.plot(numpy.arange(len(correct_labels_training)), correct_labels_training, 'k.', markersize=3, markerfacecolor='black')  
#    p11.plot(numpy.arange(len(correct_labels_training)), correct_labels_training, 'r.', markersize=3, markerfacecolor='red')  
    regression_text_labels.append("Ground Truth")
    ##draw horizontal and vertical lines
    #majorLocator   = MultipleLocator(block_size)
    #p11.xaxis.set_major_locator(majorLocator)
    ##p11.yaxis.set_major_locator(majorLocator)
    #plt.xticks(numpy.arange(0, len(labels_ccc_training), block_size)) 
    #plt.yticks(numpy.arange(0, len(labels_ccc_training), block_size)) 
    plt.xlabel(xlabel)
    plt.ylabel("Label")
    plt.legend( regression_text_labels, loc=2 )
    p11.grid(True)
    
    
    p12 = f3.add_subplot(312, frame_on=False)
    xlabel="Image Number, Seen Id Set."
    #correct_classes_seenid = numpy.arange(len(labels_ccc_seenid)) * len(labels_ccc_training) / len(labels_ccc_seenid) / block_size
    if enable_ncc_cfr:
        p12.plot(numpy.arange(len(labels_ncc_seenid)), labels_ncc_seenid, 'k.', markersize=4, markerfacecolor='black')
        xlabel += " MSE_ncc=%f,"%results.mse_ncc_seenid
    if enable_kNN_cfr:
        p12.plot(numpy.arange(len(labels_kNN_seenid)), labels_kNN_seenid, 'b.', markersize=4, markerfacecolor='blue')
        xlabel += " MSE_kNN=%f,"%results.mse_kNN_seenid
    if enable_svm_cfr:
        p12.plot(numpy.arange(len(regression_svm_seenid)), regression_svm_seenid, 'g.', markersize=4, markerfacecolor='green')
        xlabel += " MSE_svm=%f,"%results.mse_svm_seenid
    if enable_gc_cfr:
        p12.plot(numpy.arange(len(regression_Gauss_seenid)), regression_Gauss_seenid, 'm.', markersize=4, markerfacecolor='magenta')
        xlabel += " MSE_Gauss=%f,"%results.mse_gauss_seenid
    if enable_lr_cfr:
#        p12.plot(numpy.arange(len(regression_lr_seenid)), regression_lr_seenid, 'b.', markersize=4, markerfacecolor='blue')
        p12.plot(numpy.arange(len(regression_lr_seenid)), regression_lr_seenid, 'c.', markersize=4, markerfacecolor='cyan')
        xlabel += " MSE_lr=%f,"%results.mse_lr_seenid

    p12.plot(numpy.arange(len(correct_labels_seenid)), correct_labels_seenid, 'k.', markersize=4, markerfacecolor='black')
#    p12.plot(numpy.arange(len(correct_labels_seenid)), correct_labels_seenid, 'r.', markersize=4, markerfacecolor='red')

    ##majorLocator_y   = MultipleLocator(block_size)
    ##majorLocator_x   = MultipleLocator(block_size_seenid)
    #majorLocator_x   = MultipleLocator( len(labels_ccc_seenid) * block_size / len(labels_ccc_training))
    #p12.xaxis.set_major_locator(majorLocator_x)
    ##p12.yaxis.set_major_locator(majorLocator_y)
    plt.xlabel(xlabel)
    plt.ylabel("Label")
    plt.legend( regression_text_labels, loc=2 )
    p12.grid(True)
    
    
    p13 = f3.add_subplot(313, frame_on=False)
    xlabel="Image Number, New Id Set"
    if enable_ncc_cfr:
        p13.plot(numpy.arange(len(labels_kNN_newid)), labels_kNN_newid, 'k.', markersize=8, markerfacecolor='black')
        xlabel+=" MSE_ncc=%f,"%results.mse_ncc_newid
    if enable_kNN_cfr:
        p13.plot(numpy.arange(len(labels_kNN_newid)), labels_kNN_newid, 'b.', markersize=8, markerfacecolor='blue')
        xlabel+=" MSE_kNN=%f,"%results.mse_kNN_newid
    if enable_svm_cfr:
        p13.plot(numpy.arange(len(regression_svm_newid)), regression_svm_newid, 'g.', markersize=8, markerfacecolor='green')
        xlabel+=" MSE_svm=%f,"%results.mse_svm_newid
    if enable_gc_cfr:
        p13.plot(numpy.arange(len(regression_Gauss_newid)), regression_Gauss_newid, 'm.', markersize=8, markerfacecolor='magenta')
        xlabel+=" MSE_Gauss=%f,"%results.mse_gauss_newid

    if enable_lr_cfr:
#        p13.plot(numpy.arange(len(regression_lr_newid)), regression_lr_newid, 'b.', markersize=8, markerfacecolor='blue')
        p13.plot(numpy.arange(len(regression_lr_newid)), regression_lr_newid, 'c.', markersize=8, markerfacecolor='cyan')
        xlabel+=" MSE_lr=%f,"%results.mse_lr_newid

    p13.plot(numpy.arange(len(correct_labels_newid)), correct_labels_newid, 'k.', markersize=8, markerfacecolor='black')
#    p13.plot(numpy.arange(len(correct_labels_newid)), correct_labels_newid, 'r.', markersize=8, markerfacecolor='red')
   
    ##majorLocator_y   = MultipleLocator(block_size)
    ##majorLocator_x   = MultipleLocator(block_size_seenid)
    #majorLocator_x   = MultipleLocator( len(labels_ccc_newid) * block_size / len(labels_ccc_training))
    #p13.xaxis.set_major_locator(majorLocator_x)
    ##p12.yaxis.set_major_locator(majorLocator_y)
    plt.xlabel(xlabel)
    plt.ylabel("Label")
    plt.legend( regression_text_labels, loc=2 )
    p13.grid(True)
    
    
    print "************** Displaying Probability Profiles ***********"
    f4 = plt.figure()
    plt.suptitle("Probability Profiles of Gaussian Classifier Using %d Signals for Classification"%reg_num_signals)
      
    #display Probability Profile of Training Set
    ax11 = plt.subplot(1,3,1)
    plt.title("(Network) Training Set")
    #cax = p11.add_axes([1, 10, 1, 10])
    pic = ax11.imshow(probs_training, aspect='auto', interpolation='nearest', origin='upper', cmap=mpl.pyplot.cm.hot)
    plt.xlabel("Class Number")
    plt.ylabel("Image Number, Training Set")
    f4.colorbar(pic)
    
    #display Probability Profile of Seen Id
    ax11 = plt.subplot(1,3,2)
    plt.title("Seen Id Test Set")
    pic = ax11.imshow(probs_seenid, aspect='auto', interpolation='nearest', origin='upper', cmap=mpl.pyplot.cm.hot)
    plt.xlabel("Class Number")
    plt.ylabel("Image Number, Seen Id Set")
    f4.colorbar(pic)
    
    #display Probability Profile of New Id
    ax11 = plt.subplot(1,3,3)
    plt.title("New Id Test Set")
    pic = ax11.imshow(probs_newid, aspect='auto', interpolation='nearest', origin='upper', cmap=mpl.pyplot.cm.hot)
    plt.xlabel("Class Number")
    plt.ylabel("Image Number, New Id Set")
    f4.colorbar(pic)
    
    print "************ Displaying Linear (or Non-Linear) Morphs and Masks Learned by SFA **********"
    #Create Figure
    ax6 = plt.figure()
    ax6.subplots_adjust(hspace=0.3, wspace=0.03, top=0.93, right=0.96, bottom=0.05, left=0.05)
    
    #ax_6.subplots_adjust(hspace=0.5)
    plt.suptitle("Linear (or Non-Linear) Morphs using SFA")
    
    #display SFA
    ax6_11 = plt.subplot(4,5,1)
    plt.title("Train-Signals in Slow Domain")
    sl_seqdisp = sl_seq[:, range(0,hierarchy_out_dim)]
    sl_seqdisp = scale_to(sl_seqdisp, sl_seq.mean(), sl_seq.max()-sl_seq.min(), 127.5, 255.0, scale_disp, 'tanh')
    ax6_11.imshow(sl_seqdisp.clip(0,255), aspect='auto', interpolation='nearest', origin='upper', cmap=mpl.pyplot.cm.gray)
    plt.ylabel("Image number")
    #plt.xlabel("Slow Signal S[im][sl]")
    
    ax6_12 = plt.subplot(4,5,2)
    plt.title("Selected Original Image")
    ax6_12.axis('off')
    
    ax6_13 = plt.subplot(4,5,3)
    plt.title("Approx. Image x'")
    ax6_13.axis('off')
    
    ax6_14 = plt.subplot(4,5,4)
    plt.title("Re-Approx Image x''")
    ax6_14.axis('off')
    
    if show_linear_inv == True:
        ax6_15 = plt.subplot(4,5,5)
        plt.title("Avg. Image H-1(0)=z'")
        error_scale_disp=1.0
        z_p = pinv_zero
        pinv_zero_disp = scale_to(pinv_zero, pinv_zero.mean(), pinv_zero.max()-pinv_zero.min(), max_clip/2.0, max_clip, error_scale_disp, 'tanh')
        ax6_15.set_xlabel("min=%.2f, max=%.2f, std=%.2f, scale=%.2f, zero" % (pinv_zero_disp.min(), pinv_zero_disp.max(), pinv_zero_disp.std(), error_scale_disp))
        ax6_15.imshow(pinv_zero_disp.clip(0,max_clip), aspect='equal', interpolation='nearest', origin='upper', cmap=mpl.pyplot.cm.gray)
        ax6_15.axis('off')
    
    ax6_21 = plt.subplot(4,5,6)
    plt.title("H-1 (y*), y*[sl]=-2")
    plt.yticks([])
    plt.xticks([])
    plt.ylabel("Modified Projection")
    
    ax6_22 = plt.subplot(4,5,7)
    plt.title("H-1 (y*), y*[sl]=-1")
    ax6_22.axis('off')
    
    ax6_23 = plt.subplot(4,5,8)
    plt.title("H-1 (y*), y*[sl]=0")
    ax6_23.axis('off')
    
    ax6_24 = plt.subplot(4,5,9)
    plt.title("H-1 (y*), y*[sl]=1")
    ax6_24.axis('off')
    
    ax6_25 = plt.subplot(4,5,10)
    #plt.title("x' - rec S[im][sl]=2")
    plt.title("H-1 (y*), y*[sl]=2")
    ax6_25.axis('off')
    
    
    ax6_31 = plt.subplot(4,5,11)
    plt.title("x-x'+H-1(S*-S), S*[sl]=-2")
    plt.yticks([])
    plt.xticks([])
    plt.ylabel("Morph")
    
    ax6_32 = plt.subplot(4,5,12)
    plt.title("x-x'+H-1(S*-S), S*[sl]=-1")
    ax6_32.axis('off')
    
    ax6_33 = plt.subplot(4,5,13)
    plt.title("x-x'+H-1(S*-S), S*[sl]=0")
    ax6_33.axis('off')
    
    ax6_34 = plt.subplot(4,5,14)
    plt.title("x-x'+H-1(S*-S), S*[sl]=1")
    ax6_34.axis('off')
    
    ax6_35 = plt.subplot(4,5,15)
    plt.title("x-x'+H-1(S*-S), S*[sl]=2")
    ax6_35.axis('off')
    
    ax6_41 = plt.subplot(4,5,16)
    plt.title("x-x'+H-1(SFA_train[0]-S)")
    plt.yticks([])
    plt.xticks([])
    plt.ylabel("Morph from SFA_Train")
    
    ax6_42 = plt.subplot(4,5,17)
    plt.title("x-x'+H-1(SFA_train[1/4]-S)")
    ax6_42.axis('off')
    
    ax6_43 = plt.subplot(4,5,18)
    plt.title("x-x'+H-1(SFA_train[2/4]-S)")
    ax6_43.axis('off')
    
    ax6_44 = plt.subplot(4,5,19)
    plt.title("x-x'+H-1(SFA_train[3/4]-S)")
    ax6_44.axis('off')
    
    ax6_45 = plt.subplot(4,5,20)
    plt.title("x-x'+H-1(SFA_train[4/4]-S)")
    ax6_45.axis('off')
    
    print "************ Displaying Linear (or Non-Linear) Masks Learned by SFA **********"
    #Create Figure
    ax7 = plt.figure()
    ax7.subplots_adjust(hspace=0.3, wspace=0.03, top=0.93, right=0.96, bottom=0.05, left=0.05)
    
    #ax_6.subplots_adjust(hspace=0.5)
    plt.suptitle("Linear (or Non-Linear) Masks Learned by SFA [0 - 4]")
    
    mask_normalize = False
    lim_delta_sfa = 0.01
    num_masks = 4
    slow_values = [-3.0, -2.0, -1.0, 1.0, 2.0, 3.0]
    axes = range(num_masks)
    for ma in range(num_masks):
        axes[ma] = range(len(slow_values))
    
    for ma in range(num_masks):
        for sl, slow_value in enumerate(slow_values):
            tmp_ax = plt.subplot(4,6,ma*len(slow_values)+sl+1)
            plt.axes(tmp_ax)
            plt.title("H-1( S[%d]=%d ) - z'"%(ma, slow_value))
    
            if sl == 0:
                plt.yticks([])
                plt.xticks([])
                plt.ylabel("Mask[%d]"%ma)
            else:
                tmp_ax.axis('off')
            axes[ma][sl] = tmp_ax
    
    #Create Figure
    ax8 = plt.figure()
    ax8.subplots_adjust(hspace=0.3, wspace=0.03, top=0.93, right=0.96, bottom=0.05, left=0.05)
    
    #ax_6.subplots_adjust(hspace=0.5)
    plt.suptitle("Linear (or Non-Linear) Masks Learned by SFA [4 to 15]")
    
    masks2 = range(4,16) 
    num_masks2 = len(masks2)
    slow_values2 = [-1.0, 1.0]
    axes2 = range(num_masks2)
    for ma in range(num_masks2):
        axes2[ma] = range(len(slow_values2))
    
    for ma, mask in enumerate(masks2):
        for sl, slow_value in enumerate(slow_values2):
            tmp_ax = plt.subplot(4,6,ma*len(slow_values2)+sl+1)
            plt.axes(tmp_ax)
            plt.title("H-1( S[%d]=%d ) - z'"%(mask, slow_value))
            if sl == 0:
                plt.yticks([])
                plt.xticks([])
                plt.ylabel("Mask[%d]"%mask)
            else:
                tmp_ax.axis('off')
            axes2[ma][sl] = tmp_ax
    
    
    print "************ Displaying Localized Morphs and Masks **********"
    #Create Figure
    ax9 = plt.figure()
    ax9.subplots_adjust(hspace=0.3, wspace=0.03, top=0.93, right=0.96, bottom=0.05, left=0.05)
    
    #ax_6.subplots_adjust(hspace=0.5)
    plt.suptitle("Localized Linear (or Non-Linear) Morphs")
    
    ax9_11 = plt.subplot(4,5,1)
    plt.title("Train-Signals in Slow Domain")
    sl_seqdisp = sl_seq[:, range(0,hierarchy_out_dim)]
    sl_seqdisp = scale_to(sl_seqdisp, sl_seq.mean(), sl_seq.max()-sl_seq.min(), 127.5, 255.0, scale_disp, 'tanh')
    ax9_11.imshow(sl_seqdisp.clip(0,255), aspect='auto', interpolation='nearest', origin='upper', cmap=mpl.pyplot.cm.gray)
    plt.ylabel("Image number")
    
    ax9_12 = plt.subplot(4,5,2)
    plt.title("Selected Original Image")
    ax9_11.axis('off')
    
    ax9_13 = plt.subplot(4,5,3)
    plt.title("Loc. Approx. Image x'")
    ax9_12.axis('off')
    
    ax9_14 = plt.subplot(4,5,4)
    plt.title("Loc. Re-Approx Image x''")
    ax9_13.axis('off')
    
    ax9_21 = plt.subplot(4,5,6)
    plt.title("-8*Mask(cl -> cl_prev)")
    plt.yticks([])
    plt.xticks([])
    plt.ylabel("Modified Loc. Inv")
    
    ax9_22 = plt.subplot(4,5,7)
    plt.title("-4*Mask(cl -> cl_prev)")
    ax9_22.axis('off')
    
    ax9_23 = plt.subplot(4,5,8)
    plt.title("2*Mask(cl -> cl_prev)")
    ax9_23.axis('off')
    
    ax9_24 = plt.subplot(4,5,9)
    plt.title("4*Mask(cl -> cl_prev)")
    ax9_24.axis('off')
    
    ax9_25 = plt.subplot(4,5,10)
    plt.title("8*Mask(cl -> cl_prev)")
    ax9_25.axis('off')
    
    print "************ Displaying Localized Morphs Learned by SFA **********"
    #Create Figure
    ax10 = plt.figure()
    ax10.subplots_adjust(hspace=0.3, wspace=0.03, top=0.93, right=0.96, bottom=0.05, left=0.05)
    
    num_morphs = 20
    morph_step = 0.5
    all_axes_morph_inc = []
    all_classes_morph_inc = numpy.arange(num_morphs)*morph_step
    for i in range(len(all_classes_morph_inc)):
        tmp_ax = plt.subplot(4,5,i+1)
        plt.title("Morph(cl* -> cl*)")
        tmp_ax.axis('off')
        all_axes_morph_inc.append(tmp_ax)
    
    
    ax11 = plt.figure()
    ax11.subplots_adjust(hspace=0.3, wspace=0.03, top=0.93, right=0.96, bottom=0.05, left=0.05)
    
    all_axes_morph_dec = []
    all_classes_morph_dec = numpy.arange(0, -1 * num_morphs, -1) * morph_step
    for i in range(len(all_classes_morph_dec)):
        tmp_ax = plt.subplot(4, 5,20-i)
        plt.title("Morph (cl*-> cl*)")
        tmp_ax.axis('off')
        all_axes_morph_dec.append(tmp_ax)
    
    #morphed sequence in SFA domain
    ax12 = plt.figure()
    ax12_1 = plt.subplot(2, 2, 1)
    plt.title("SFA of Morphed Images")
    ax12_2 = plt.subplot(2, 2, 2)
    plt.title("Average SFA for each Class")
    sl_seq_meandisp = scale_to(sl_seq_training_mean, sl_seq_training_mean.mean(), sl_seq_training_mean.max()-sl_seq_training_mean.min(), 127.5, 255.0, scale_disp, 'tanh')
    ax12_2.imshow(sl_seq_meandisp.clip(0, 255), aspect='auto', interpolation='nearest', origin='upper', cmap=mpl.pyplot.cm.gray)
    ax12_3 = plt.subplot(2, 2, 3)
    plt.title("SFA of Selected Image")
    
    print "************ Displaying Localized) Morphs Learned by SFA **********"
    #Create Figure
    ax13 = plt.figure()
    ax13.subplots_adjust(hspace=0.3, wspace=0.03, top=0.93, right=0.96, bottom=0.05, left=0.05)
    
    all_axes_mask_inc = []
    for i in range(len(all_classes_morph_inc)):
        tmp_ax = plt.subplot(4,5,i+1)
        plt.title("Mask(cl* -> cl*)")
        tmp_ax.axis('off')
        all_axes_mask_inc.append(tmp_ax)
    
    ax14 = plt.figure()
    ax14.subplots_adjust(hspace=0.3, wspace=0.03, top=0.93, right=0.96, bottom=0.05, left=0.05)
    
    all_axes_mask_dec = []
    for i in range(len(all_classes_morph_dec)):
        tmp_ax = plt.subplot(4, 5,20-i)
        plt.title("Mask (cl*-> cl*)")
        tmp_ax.axis('off')
        all_axes_mask_dec.append(tmp_ax)
    

##ax_6.subplots_adjust(hspace=0.5)
#plt.suptitle("Localized Linear (or Non-Linear) Masks Learned by SFA [0 - 4]")
#lim_delta_sfa = 0.001
#num_masks3 = 4
#slow_values3 = [-3.0, -2.0, -1.0, 1.0, 2.0, 3.0]
#axes3 = range(num_masks3)
#for ma in range(num_masks3):
#    axes3[ma] = range(len(slow_values3))
#
#for ma in range(num_masks3):
#    for sl, slow_value in enumerate(slow_values3):
#        tmp_ax = plt.subplot(4,6,ma*len(slow_values3)+sl+1)
#        plt.axes(tmp_ax)
#        plt.title("H-1( S[%d]=%d ) - z'"%(ma, slow_value))
#
#        if sl == 0:
#            plt.yticks([])
#            plt.xticks([])
#            plt.ylabel("Mask[%d]"%ma)
#        else:
#            tmp_ax.axis('off')
#        axes3[ma][sl] = tmp_ax
#
##Create Figure
#ax11 = plt.figure()
#ax11.subplots_adjust(hspace=0.3, wspace=0.03, top=0.93, right=0.96, bottom=0.05, left=0.05)
#
##ax_6.subplots_adjust(hspace=0.5)
#plt.suptitle("Linear (or Non-Linear) Masks Learned by SFA [4 to 15]")
#
#masks4 = range(4,16) 
#num_masks4 = len(masks4)
#slow_values4 = [-1.0, 1.0]
#axes4 = range(num_masks4)
#for ma in range(num_masks4):
#    axes4[ma] = range(len(slow_values4))
#
#for ma, mask in enumerate(masks4):
#    for sl, slow_value in enumerate(slow_values4):
#        tmp_ax = plt.subplot(4,6,ma*len(slow_values4)+sl+1)
#        plt.axes(tmp_ax)
#        plt.title("H-1( S[%d]=%d ) - z'"%(mask, slow_value))
#        if sl == 0:
#            plt.yticks([])
#            plt.xticks([])
#            plt.ylabel("Mask[%d]"%mask)
#        else:
#            tmp_ax.axis('off')
#        axes4[ma][sl] = tmp_ax


#UNCOMMENT THIS!!!! and add code to show result of localized inversion
#print "************ Displaying Localized Morphs and Masks **********"
##Create Figure
#ax9 = plt.figure()
#ax9.subplots_adjust(hspace=0.3, wspace=0.03, top=0.93, right=0.96, bottom=0.05, left=0.05)
#
##ax_6.subplots_adjust(hspace=0.5)
#plt.suptitle("Localized (Linear or Non-Linear) Morphs using SFA")
#
##display SFA
#ax9_11 = plt.subplot(4,5,1)
#plt.title("Train-Signals in Slow Domain")
#sl_seqdisp = sl_seq[:, range(0,hierarchy_out_dim)]
#sl_seqdisp = scale_to(sl_seqdisp, sl_seq.mean(), sl_seq.max()-sl_seq.min(), 127.5, 255.0, scale_disp, 'tanh')
#ax9_11.imshow(sl_seqdisp.clip(0,255), aspect='auto', interpolation='nearest', origin='upper', cmap=mpl.pyplot.cm.gray)
#plt.ylabel("Image number")
#
#mask_normalize = False
#lim_delta_sfa = 0.001
#num_masks = 4
#slow_values = [-3.0, -2.0, -1.0, 1.0, 2.0, 3.0]
#axes = range(num_masks)
#for ma in range(num_masks):
#    axes[ma] = range(len(slow_values))
#
#for ma in range(num_masks):
#    for sl, slow_value in enumerate(slow_values):
#        tmp_ax = plt.subplot(4,6,ma*len(slow_values)+sl+1)
#        plt.axes(tmp_ax)
#        plt.title("H-1( S[%d]=%d ) - z'"%(ma, slow_value))
#
#        if sl == 0:
#            plt.yticks([])
#            plt.xticks([])
#            plt.ylabel("Mask[%d]"%ma)
#        else:
#            tmp_ax.axis('off')
#        axes[ma][sl] = tmp_ax



    #Retrieve Image in Sequence
    def mask_on_press(event):
        global plt, ax6, ax6_11, ax6_12, ax6_13, ax6_14, ax6_21, ax6_22, ax6_23, ax6_24, ax6_25, ax6_31, ax6_32, ax6_33, ax6_34, ax6_35, ax6_41, ax6_42, ax6_43, ax6_44, ax6_45
        global ax7, axes, num_masks, slow_values, mask_normalize, lim_delta_sfa
        global ax8, axes2, masks2, slow_values2
        global ax9, ax9_11, ax9_12, ax9_13, ax9_14, ax9_21, ax9_22, ax9_23, ax9_24, ax9_25
    
        global subimages, sTrain, sl_seq, pinv_zero, flow, error_scale_disp
        
        print 'you pressed', event.button, event.xdata, event.ydata
    
        if event.xdata == None or event.ydata==None:
            mask_normalize = not mask_normalize
            print "mask_normalize is: ", mask_normalize
            return
        
        y = int(event.ydata)
        if y < 0:
            y = 0
        if y >= num_images:
            y = num_images - 1
        x = int(event.xdata)
        if x < 0:
            x = 0
        if x >= hierarchy_out_dim:
            x = hierarchy_out_dim -1
        print "Image Selected=" + str(y) + " , Slow Component Selected=" + str(x)
    
        print "Displaying Original and Reconstructions"
    #Display Original Image
        subimage_im = subimages[y].reshape(subimage_shape)
        ax6_12.imshow(subimage_im.clip(0,max_clip), vmin=0, vmax=max_clip, aspect='equal', interpolation='nearest', origin='upper', cmap=mpl.pyplot.cm.gray)
    
        if show_linear_inv == True:
            #Display Reconstructed Image
            data_out = sl_seq[y].reshape((1, hierarchy_out_dim))
            inverted_im = flow.inverse(data_out)
            inverted_im = inverted_im.reshape(subimage_shape)
            x_p = inverted_im
            inverted_im_ori = inverted_im.copy()
            ax6_13.imshow(inverted_im.clip(0,max_clip), vmin=0, vmax=max_clip, aspect='equal', interpolation='nearest', origin='upper', cmap=mpl.pyplot.cm.gray)        
        
            #Display Re-Reconstructed Image
            re_data_out = flow.execute(inverted_im_ori.reshape((1, signals_per_image)))
            re_inverted_im = flow.inverse(re_data_out)
            re_inverted_im = re_inverted_im.reshape(subimage_shape)
            ax6_14.imshow(re_inverted_im.clip(0,max_clip), vmin=0, vmax=max_clip, aspect='equal', interpolation='nearest', origin='upper', cmap=mpl.pyplot.cm.gray)
        
        if show_linear_morphs == True:   
            print "Displaying Morphs, Original Version, no localized inverses"
            #Display: Altered Reconstructions
            #each tuple has the form: (val of slow_signal, remove, axes for display)
            #where remove is None, "avg" or "ori"
            error_scale_disp=1.0
            disp_data = [(-2, "inv", ax6_21), (-1, "inv", ax6_22), (0, "inv", ax6_23), (1, "inv", ax6_24), (2, "inv", ax6_25), \
                         (-2, "mor", ax6_31), (-1, "mor", ax6_32), (0, "mor", ax6_33), (1, "mor", ax6_34), (2, "mor", ax6_35), 
                         (-2, "mo2", ax6_41), (-1, "mo2", ax6_42), (0, "mo2", ax6_43), (1, "mo2", ax6_44), (2, "mo2", ax6_45)]
          
            work_sfa = data_out.copy()
               
            for slow_value, display_type, fig_axes in disp_data:
                work_sfa[0][x] = slow_value
                inverted_im = flow.inverse(work_sfa)
                inverted_im = inverted_im.reshape(subimage_shape)
                if display_type == "inv":
                    fig_axes.imshow(inverted_im.clip(0,max_clip), vmin=0, vmax=max_clip, aspect='equal', interpolation='nearest', origin='upper', cmap=mpl.pyplot.cm.gray)        
                elif display_type == "mor":
                    # delta_sfa = sfa*-sfa
                    delta_sfa = numpy.zeros((1, hierarchy_out_dim))
                    delta_sfa[0][x] = slow_value
                    delta_im = flow.inverse(delta_sfa)
                    delta_im = delta_im.reshape(subimage_shape)                      
                    morphed_im = subimage_im - x_p + delta_im
        #            morphed_im = subimage_im - x_p + inverted_im - z_p
        #            morphed_im = morphed.reshape((sTrain.subimage_height, sTrain.subimage_width))           
        #            inverted_im = inverted_im - pinv_zero
        #            inverted_im_disp = scale_to(inverted_im, inverted_im.mean(), inverted_im.max()-inverted_im.min(), 127.5, 255.0, error_scale_disp, 'tanh')
        #            morphed_im_disp = scale_to(morphed_im, morphed_im.mean(), morphed_im.max()-morphed_im.min(), 127.5, 255.0, error_scale_disp, 'tanh')
                    morphed_im_disp = morphed_im
                    fig_axes.imshow(morphed_im_disp.clip(0,max_clip), vmin=0, vmax=max_clip, aspect='equal', interpolation='nearest', origin='upper', cmap=mpl.pyplot.cm.gray)        
                elif display_type == "mo2":
                    # delta_sfa = sfa*-sfa
                    sfa_asterix = sl_seq[(slow_value + 2) * (num_images-1) / 4].reshape((1, hierarchy_out_dim))
                    delta_sfa = sfa_asterix - data_out
                    delta_im = flow.inverse(delta_sfa)
                    delta_im = delta_im.reshape(subimage_shape)                      
                    morphed_im = subimage_im - x_p + delta_im
                    morphed_im_disp = morphed_im
                    fig_axes.imshow(morphed_im_disp.clip(0,max_clip), vmin=0, vmax=max_clip, aspect='equal', interpolation='nearest', origin='upper', cmap=mpl.pyplot.cm.gray)                 
        ax6.canvas.draw()
    
        if show_linear_masks == True:  
            print "Displaying Masks [0-3]"
            for ma in range(num_masks):
                for sl, slow_value in enumerate(slow_values):
                    tmp_ax = axes[ma][sl]
    
                    print "Computing mask %d, slow_value %d"%(ma, slow_value)
                    work_sfa = data_out.copy()
                    work_sfa[0][ma] = work_sfa[0][ma] + slow_value * lim_delta_sfa
                    mask_im = flow.inverse(work_sfa)
                    mask_im = (mask_im.reshape(subimage_shape) - x_p) / lim_delta_sfa
                    if mask_normalize == True:
                        mask_im_disp = scale_to(mask_im, 0.0, mask_im.max()-mask_im.min(), max_clip/2.0, max_clip/2.0, error_scale_disp, 'tanh')
                    else:
                        mask_im_disp = mask_im + max_clip/2.0
                    axes[ma][sl].imshow(mask_im_disp.clip(0,max_clip), vmin=0, vmax=max_clip, aspect='equal', interpolation='nearest', origin='upper', cmap=mpl.pyplot.cm.gray)          
            ax7.canvas.draw()
            
        if show_linear_masks_ext == True:  
            print "Displaying Masks [4-15]"
            for ma, mask in enumerate(masks2):
                for sl, slow_value in enumerate(slow_values2):
                    tmp_ax = axes2[ma][sl]
                    work_sfa = data_out.copy()
                    work_sfa[0][mask] += slow_value * lim_delta_sfa
                    mask_im = flow.inverse(work_sfa)
                    mask_im = (mask_im.reshape(subimage_shape) - x_p) / lim_delta_sfa
                    if mask_normalize == True:
                        mask_im_disp = scale_to(mask_im, 0.0, mask_im.max()-mask_im.min(), max_clip/2.0, max_clip, error_scale_disp, 'tanh')
                    else:
                        mask_im_disp = mask_im + max_clip/2.0
                    axes2[ma][sl].imshow(mask_im_disp.clip(0,max_clip), vmin=0, vmax=max_clip, aspect='equal', interpolation='nearest', origin='upper', cmap=mpl.pyplot.cm.gray)          
            ax8.canvas.draw()
    
    ax6.canvas.mpl_connect('button_press_event', mask_on_press)
    
    #QUESTION: WHEN SHOULD I USE THE KEYWORK global?????
    def localized_on_press(event):
        global plt, ax9, ax9_11, ax9_12, ax9_13, ax9_14, ax9_21, ax9_22, ax9_23, ax9_24, ax9_25
        global ax9_31, ax9_32, ax9_33, ax9_34, ax9_35
        global ax9_41, ax9_42, ax9_43, ax9_44, ax9_45
        global subimages, sTrain, sl_seq, flow, error_scale_disp, hierarchy_out_dim
        global mask_normalize, lim_delta_sfa, correct_classes_training, S2SC, block_size
        global ax10, ax11, all_axes_morph
        global ax13, ax14
        
        print 'you pressed', event.button, event.xdata, event.ydata
    
        if event.xdata == None or event.ydata==None:
            mask_normalize = not mask_normalize
            print "mask_normalize was successfully changed to: ", mask_normalize
            return
        
        y = int(event.ydata)
        if y < 0:
            y = 0
        if y >= num_images:
            y = num_images - 1
        x = int(event.xdata)
        if x < 0:
            x = 0
        if x >= hierarchy_out_dim:
            x = hierarchy_out_dim -1
        print "Image Selected=" + str(y) + " , Slow Component Selected=" + str(x)
    
        print "Displaying Original and Reconstructions"
    #Display Original Image
        subimage_im = subimages[y].reshape(subimage_shape)
        ax9_12.imshow(subimage_im.clip(0,max_clip), vmin=0, vmax=max_clip, aspect='equal', interpolation='nearest', origin='upper', cmap=mpl.pyplot.cm.gray)
    
        if show_localized_morphs == True: 
            #Display Localized Reconstructed Image
            data_in = subimages[y].reshape((1, signals_per_image))
            data_out = sl_seq[y].reshape((1, hierarchy_out_dim))
            loc_inverted_im = flow.localized_inverse(data_in, data_out)
            loc_inverted_im = loc_inverted_im.reshape(subimage_shape)
            loc_inverted_im_ori = loc_inverted_im.copy()
            ax9_13.imshow(loc_inverted_im.clip(0,max_clip), vmin=0, vmax=max_clip, aspect='equal', interpolation='nearest', origin='upper', cmap=mpl.pyplot.cm.gray)        
        
            #Display Re-Reconstructed Image
            loc_re_data_in = loc_inverted_im_ori.reshape((1, signals_per_image))
            loc_re_data_out = flow.execute(loc_re_data_in)
            loc_re_inverted_im = flow.localized_inverse(loc_re_data_in, loc_re_data_out)
            loc_re_inverted_im = loc_re_inverted_im.reshape(subimage_shape)
            ax9_14.imshow(loc_re_inverted_im.clip(0,max_clip), vmin=0, vmax=max_clip, aspect='equal', interpolation='nearest', origin='upper', cmap=mpl.pyplot.cm.gray)
            
            print "Displaying Masks Using Localized Inverses"
            error_scale_disp=1.0
            disp_data = [(-8, "lmsk", ax9_21), (-4.0, "lmsk", ax9_22), (2.0, "lmsk", ax9_23), (4.0, "lmsk", ax9_24), (8.0, "lmsk", ax9_25)]
        
            data_in = subimages[y].reshape((1, signals_per_image))
            data_out = sl_seq[y].reshape((1, hierarchy_out_dim))  
            work_sfa = data_out.copy()
               
            for scale_factor, display_type, fig_axes in disp_data:
                #WARNING, this should not be computed this way!!!!
                current_class = y/block_size
                print "Current classs is:", current_class
                if scale_factor < 0:
                    next_class = current_class-1
                    if next_class < 0:
                        next_class = 0
                else:
                    next_class = current_class+1
                    if next_class >= hierarchy_out_dim:
                        next_class = hierarchy_out_dim-1
                    
                current_avg_sfa = sl_seq[current_class * block_size:(current_class+1)*block_size,:].mean(axis=0)
                next_avg_sfa = sl_seq[next_class*block_size:(next_class+1)*block_size,:].mean(axis=0)
                        
                print "Current class is ", current_class
                #print "Current class_avg is ", current_avg_sfa
                #print "Next class_avg is ", next_avg_sfa
                
                data_out_next = next_avg_sfa
                print "Computing from class %d to class %d, slow_value %d"%(current_class, next_class, scale_factor)
                work_sfa = data_out * (1-lim_delta_sfa) + data_out_next * lim_delta_sfa
                t_loc_inv0 = time.time()
                mask_im = flow.localized_inverse(data_in, work_sfa, verbose=False)
                t_loc_inv1 = time.time()
                print "Localized inverse computed in %0.3f s"% ((t_loc_inv1-t_loc_inv0)) 
                mask_im = (mask_im - data_in).reshape(subimage_shape) / lim_delta_sfa
                if mask_normalize == True:
                    mask_im_disp = abs(scale_factor) * scale_to(mask_im, 0.0, mask_im.max()-mask_im.min(), max_clip/2.0, max_clip/2.0, error_scale_disp, 'tanh')
                else:
                    mask_im_disp = abs(scale_factor) * mask_im + max_clip/2.0
                fig_axes.imshow(mask_im_disp.clip(0,max_clip), vmin=0, vmax=max_clip, aspect='equal', interpolation='nearest', origin='upper', cmap=mpl.pyplot.cm.gray)           
                fig_axes.set_title('%0.2f x Mask: cl %d => %d'%(abs(scale_factor), current_class, next_class))
            ax9.canvas.draw()
            
            error_scale_disp=1.0
            print "Displaying Morphs Using Localized Inverses Incrementing Class"
    
            num_morphs_inc = len(all_classes_morph_inc)
            num_morphs_dec = len(all_classes_morph_dec)
            #make a function specialized in morphs, use this variable,
            morph_outputs =  range(num_morphs_inc + num_morphs_dec - 1)
            morph_sfa_outputs = range(num_morphs_inc + num_morphs_dec - 1)
            original_class = y/block_size
    
    
            #WARNING!!! THERE IS A BUG, IN WHICH THE LAST INC MORPHS ARE INCORRECTLY COMBINED USING ZERO??? 
            for ii, action in enumerate(["inc", "dec"]):
                current_class = original_class
                if ii==0:
                    all_axes_morph = all_axes_morph_inc
                    all_axes_mask = all_axes_mask_inc
                    num_morphs = len(all_classes_morph_inc)
                    desired_next_classes = all_classes_morph_inc + current_class
                    max_class = num_images/block_size
                    for i in range(len(desired_next_classes)):
                        if desired_next_classes[i] >= max_class:
                            desired_next_classes[i] = -1
                else:                
                    all_axes_morph = all_axes_morph_dec
                    all_axes_mask = all_axes_mask_dec
                    num_morphs = len(all_classes_morph_dec)
                    desired_next_classes = all_classes_morph_dec + current_class
                    for i in range(len(desired_next_classes)):
                        if desired_next_classes[i] < 0:
                            desired_next_classes[i] = -1
    
                desired_next_sfa=[]
                for next_class in desired_next_classes:
                    if next_class >= 0 and next_class < max_class:
                        c1 = numpy.floor(next_class)
                        c2 = c1  + 1               
                        if c2 >= max_class:
                            c2 = max_class-1 
                        desired_next_sfa.append(sl_seq_training_mean[c1] * (1+c1-next_class) + sl_seq_training_mean[c2]*(next_class-c1))
                    else: #just in case something goes wrong
                        desired_next_sfa.append(sl_seq_training_mean[0])
                    #sl_seq[next_class*block_size:(next_class+1)*block_size,:].mean(axis=0))
        
                data_in = subimages[y].reshape((1, signals_per_image))
                data_out = sl_seq[y].reshape((1, hierarchy_out_dim))
                for i, next_class in enumerate(desired_next_classes):
                    if next_class == -1:
                        if ii==0:
                            morph_sfa_outputs[i+num_morphs_dec-1] = numpy.zeros(len(data_out[0])) 
                        else:
                            morph_sfa_outputs[num_morphs_dec-i-1] = numpy.zeros(len(data_out[0]))
                        break          
                    data_out_next = desired_next_sfa[i]           
                    print "Morphing to desired class %.2f..."%next_class
                    
                    work_sfa = data_out * (1-lim_delta_sfa) + data_out_next * lim_delta_sfa
        
                    t_loc_inv0 = time.time()
                    morphed_data = flow.localized_inverse(data_in, work_sfa, verbose=False)
                    t_loc_inv1 = time.time()
                    print "Localized inverse computed in %0.3f s"% ((t_loc_inv1-t_loc_inv0)) 
                    
                    morphed_data = data_in + (morphed_data - data_in)/lim_delta_sfa
                    morphed_im_disp = morphed_data.reshape(subimage_shape) 
        
                    if all_axes_morph[i] != None:
                        all_axes_morph[i].imshow(morphed_im_disp.clip(0,max_clip), vmin=0, vmax=max_clip, aspect='equal', interpolation='nearest', origin='upper', cmap=mpl.pyplot.cm.gray)           
                        all_axes_morph[i].set_title("Morph(cl %.1f -> %.1f)"%(current_class,next_class))
                    else:
                        print "No plotting Morph. (Reason: axes = None)"
    
                    if all_axes_mask[i] != None:
                        loc_mask_data = morphed_data[0] - data_in[0]
                        loc_mask_disp = loc_mask_data.reshape(subimage_shape) + max_clip/2.0
                        loc_mask_disp = scale_to(loc_mask_disp, loc_mask_disp.mean(), loc_mask_disp.max() - loc_mask_disp.min(), 127.5, 255.0, scale_disp, 'tanh')
                        all_axes_mask[i].imshow(loc_mask_disp.clip(0,max_clip), vmin=0, vmax=max_clip, aspect='equal', interpolation='nearest', origin='upper', cmap=mpl.pyplot.cm.gray)           
                        all_axes_mask[i].set_title("Mask(cl %.1f -> %.1f)"%(current_class,next_class))
                    else:
                        print "No plotting Mask. (Reason: axes = None)"
                    
                    current_class = next_class
                    data_in = morphed_data
                    data_out = flow.execute(data_in)
                    if ii==0: #20-29
                        morph_sfa_outputs[i+num_morphs_dec-1] = data_out[0]
                    else: #0-19
                        morph_sfa_outputs[num_morphs_dec-i-1] = data_out[0]
                       
            ax10.canvas.draw()
            ax11.canvas.draw()
            ax13.canvas.draw()
            ax14.canvas.draw()
    
    #        for i, sfa_out in enumerate(morph_sfa_outputs):
    #            print "elem %d: "%i, "has shape", sfa_out.shape, "and is= ", sfa_out
    
    #        morph_sfa_outputs[num_morphs_dec] = sl_seq[y]
            sl_morph = numpy.array(morph_sfa_outputs)
            sl_morphdisp = scale_to(sl_morph, sl_morph.mean(), sl_morph.max()-sl_morph.min(), 127.5, 255.0, scale_disp, 'tanh')
    #        extent = (L, R, B, U)
            extent = (0, hierarchy_out_dim-1, all_classes_morph_inc[-1]+original_class, all_classes_morph_dec[-1]+original_class-0.25)
            ax12_1.imshow(sl_morphdisp.clip(0,255), aspect='auto', interpolation='nearest', origin='upper', cmap=mpl.pyplot.cm.gray, extent=extent)
    #        majorLocator_y   = MultipleLocator(0.5)
    #        ax12_1.yaxis.set_major_locator(majorLocator_y)
            plt.ylabel("Morphs")
            
     
            sl_selected = sl_seq[y][:].reshape((1, hierarchy_out_dim))
            sl_selected = scale_to(sl_selected, sl_selected.mean(), sl_selected.max()-sl_selected.min(), 127.5, 255.0, scale_disp, 'tanh')
    #        extent = (0, hierarchy_out_dim-1, all_classes_morph_inc[-1]+original_class+0.5, all_classes_morph_dec[-1]+original_class-0.5)
            ax12_3.imshow(sl_selected.clip(0,255), aspect=8.0, interpolation='nearest', origin='upper', cmap=mpl.pyplot.cm.gray)
    #        majorLocator_y   = MultipleLocator(0.5)
    #        ax12_1.yaxis.set_major_locator(majorLocator_y)
    #        plt.ylabel("Morphs")
    
                  
    #        morphed_classes = numpy.concatenate((all_classes_morph_dec[::-1], [0], all_classes_morph_inc))
    #        print "morphed_classes=", morphed_classes
    #        morphed_classes = morphed_classes + original_class
    #        majorLocator_y   = MultipleLocator(1)
    #        #ax12_1.yticks(morphed_classes) 
    #        ax12_1.yaxis.set_major_locator(majorLocator_y)
            ax12.canvas.draw()
            
    ax9.canvas.mpl_connect('button_press_event', localized_on_press)

    if compute_slow_features_newid_across_net:
        if compute_slow_features_newid_across_net == 2:
            print "Displaying slowest component across network"
            relevant_out_dim = 1
            first_feature = 0
            transpose_plot = False
            two_feats = False
        elif compute_slow_features_newid_across_net == 3:
            print "Displaying second slowest component across network, vertically"
            relevant_out_dim = 1
            first_feature = 1
            transpose_plot = True
            two_feats = False
        elif compute_slow_features_newid_across_net == 4:
            print "Displaying second against first slowest component across network"
            relevant_out_dim = 2
            first_feature = 0
            transpose_plot = False
            two_feats = True
        else:
            print "Displaying first %d slowest components across network"%relevant_out_dim
            transpose_plot = False
            first_feature = 0
            two_feats = False
            
        print "************ Displaying Slow Features Across Network (Newid) **********"
        #Create Figure
        
        ax = plt.figure()
        #ax13.subplots_adjust(hspace=0.3, wspace=0.03, top=0.93, right=0.96, bottom=0.05, left=0.05)
        
        sfa_nodes_or_layers_indices = []
        for i, node in enumerate(flow.flow):
            if isinstance(node, (mdp.hinet.Layer, mdp.hinet.CloneLayer)):
                if isinstance(node.nodes[0], mdp.nodes.SFANode):
                    sfa_nodes_or_layers_indices.append(i)
            elif isinstance(node, mdp.nodes.SFANode):
                    sfa_nodes_or_layers_indices.append(i)    
        
        num_sfa_nodes_or_layers = len(sfa_nodes_or_layers_indices)
        print "num_sfa_nodes_or_layers=", num_sfa_nodes_or_layers
        for plot_nr, node_i in enumerate(sfa_nodes_or_layers_indices):
            flow_partial = flow[0:node_i+1]
            sl_partial = flow_partial.execute(subimages_newid)

            if transpose_plot:
                plt.subplot((num_sfa_nodes_or_layers-1)/3+1,3,plot_nr+1)           
            else:
                plt.subplot(2, (num_sfa_nodes_or_layers-1)/2+1,plot_nr+1)           

            node = flow.flow[node_i]
            if isinstance(node, (mdp.hinet.Layer, mdp.hinet.CloneLayer)):
                num_nodes = len(node.nodes)                
                central_node_nr = num_nodes / 2 + int((num_nodes**0.5))/2
                z = sl_partial.shape[1]/num_nodes
                sl_partial = sl_partial[:, z*central_node_nr:z*(central_node_nr+1)]
                print "num_nodes=", num_nodes, "central_node_nr=", central_node_nr, "sl_partial.shape=", sl_partial.shape
                plt.title("SFA Outputs. Node %d, subnode %d "%(node_i, central_node_nr))
            else:                
                plt.title("SFA Outputs. Node %d"%(node_i))
            
            if two_feats == False:
                #TODO: Notice conflict between (relevant_sfa_indices deprecated) and reversed_sfa_indices
                relevant_sfa_indices = numpy.arange(relevant_out_dim) 
                reversed_sfa_indices = range(first_feature, relevant_out_dim+first_feature)
                reversed_sfa_indices.reverse()
            
                r_color = (1-relevant_sfa_indices * 1.0 / relevant_out_dim) * 0.8 + 0.2
                g_color = (relevant_sfa_indices * 1.0 / relevant_out_dim) * 0.8 + 0.2
                b_color = relevant_sfa_indices * 0.0
                r_color = [1.0, 0.0, 0.0]
                g_color = [28/255.0, 251/255.0, 55/255.0]
                b_color = [33/255.0, 79/255.0, 196/255.0]   
                if relevant_out_dim == 1:
                    r_color = [0.0]*3
                    g_color = [55/255.0]*3
                    b_color = [196/255.0]*3
                    
                max_amplitude_sfa = 3.0 # 2.0
            
                sfa_text_labels = ["Slowest Signal", "2nd Slowest Signal", "3rd Slowest Signal"]
            
                for sig in reversed_sfa_indices:
                    if transpose_plot == False:
                        plt.plot(numpy.arange(num_images_newid), sl_partial[:, sig], ".", color=(r_color[sig], g_color[sig], b_color[sig]), label=sfa_text_labels[sig], markersize=6, markerfacecolor=(r_color[sig], g_color[sig], b_color[sig]))
                        plt.ylim(-max_amplitude_sfa, max_amplitude_sfa)
                    else:
                        plt.plot(sl_partial[:, sig], numpy.arange(num_images_newid), ".", color=(r_color[sig], g_color[sig], b_color[sig]), label=sfa_text_labels[sig], markersize=6, markerfacecolor=(r_color[sig], g_color[sig], b_color[sig]))
                        plt.xlim(-max_amplitude_sfa, max_amplitude_sfa)
                
                #plt.xlabel("Input Image, Training Set (red=slowest signal, light green=fastest signal)")
                #plt.ylabel("Slow Signals")
            else: #Second component vs First component
                r_color = 0.0
                g_color = 55/255.0
                b_color = 196/255.0   
                max_amplitude_sfa = 3.0 # 2.0
                       
                if transpose_plot == False:
                    #Typically: plot 2nd slowest feature against first one
                    plt.plot(sl_partial[:, 1], sl_partial[:, 0], ".", color=(r_color, g_color, b_color), markersize=6, markerfacecolor=(r_color, g_color, b_color))
                else:
                    plt.plot(sl_partial[:, 0], sl_partial[:, 1], ".", color=(r_color, g_color, b_color), markersize=6, markerfacecolor=(r_color, g_color, b_color))
                
                plt.xlim(-max_amplitude_sfa, max_amplitude_sfa)
                plt.ylim(-max_amplitude_sfa, max_amplitude_sfa)
                
                #plt.xlabel("Input Image, Training Set (red=slowest signal, light green=fastest signal)")
                #plt.ylabel("Slow Signals")
                

#            work_sfa[0][x] = slow_value
#            t_loc_inv0 = time.time()
#            inverted_im = flow.localized_inverse(data_in, work_sfa, verbose=True)
#            t_loc_inv1 = time.time()
#            print "Localized inverse computed in %0.3f ms"% ((t_loc_inv1-t_loc_inv0)*1000.0) 
#
#            inverted_im = inverted_im.reshape((sTrain.subimage_height, sTrain.subimage_width))
#            if display_type == "inv":
#                fig_axes.imshow(inverted_im.clip(0,255), vmin=0, vmax=255, aspect='equal', interpolation='nearest', origin='upper', cmap=mpl.pyplot.cm.gray)        
        
#        print "Displaying Masks Using Localized Inverses"
#        #Display: Altered Reconstructions
#        error_scale_disp=1.0
#        disp_data = [(-1, "inv", ax9_21), (-0.5, "inv", ax9_22), (0, "inv", ax9_23), (0.5, "inv", ax9_24), (1, "inv", ax9_25)]
#    
#        data_in = subimages[y].reshape((1, sTrain.subimage_height * sTrain.subimage_width))
#        data_out = sl_seq[y].reshape((1, hierarchy_out_dim))  
#        work_sfa = data_out.copy()
#           
#        for slow_value, display_type, fig_axes in disp_data:
#            work_sfa[0][x] = slow_value
#            t_loc_inv0 = time.time()
#            inverted_im = flow.localized_inverse(data_in, work_sfa, verbose=True)
#            t_loc_inv1 = time.time()
#            print "Localized inverse computed in %0.3f ms"% ((t_loc_inv1-t_loc_inv0)*1000.0) 
#
#            inverted_im = inverted_im.reshape((sTrain.subimage_height, sTrain.subimage_width))
#            if display_type == "inv":
#                fig_axes.imshow(inverted_im.clip(0,255), vmin=0, vmax=255, aspect='equal', interpolation='nearest', origin='upper', cmap=mpl.pyplot.cm.gray)        


    print "GUI Created, showing!!!!"
    plt.show()
    print "GUI Finished!"


   
print "Program successfully finished"

#    def __init__(self):
#        self.name = "Training Data"
#        self.num_samples = 0
#        self.sl = []
#        self.correct_classes = []
#        self.correct_labels = []
#        self.classes = []
#        self.labels = []
#        self.block_size = []
#        self.eta_values = []
#        self.delta_values = []
#        self.class_ccc_rate = 0
#        self.gauss_class_rate = 0
#        self.reg_mse = 0
#        self.gauss_reg_mse = 0


#im_seq_base_dir = pFTrain.data_base_dir
#ids = pFTrain.ids
#ages = pFTrain.ages
#MIN_GENDER = pFTrain.MIN_GENDER
#MAX_GENDER = pFTrain.MAX_GENDER
#GENDER_STEP = pFTrain.GENDER_STEP
#genders = map(code_gender, numpy.arange(MIN_GENDER, MAX_GENDER,GENDER_STEP))
#racetweens = pFTrain.racetweens
#expressions = pFTrain.expressions 
#morphs = pFTrain.morphs 
#poses = pFTrain.poses
#lightings = pFTrain.lightings
#slow_signal = pFTrain.slow_signal
#step = pFTrain.step
#offset = pFTrain.offset
#
#image_files_training = create_image_filenames2(im_seq_base_dir, slow_signal, ids, ages, genders, racetweens, \
#                            expressions, morphs, poses, lightings, step, offset)

#params = [ids, expressions, morphs, poses, lightings]
#params2 = [ids, ages, genders, racetweens, expressions, morphs, poses, lightings]

#block_size= num_images / len(params[slow_signal])
#block_size = num_images / len(params2[slow_signal])

##translation = 4
#translation = pDataTraining.translation 
#
##WARNING
##scale_disp = 3
#scale_disp = 1
##image_width  = 640
##image_height = 480
#image_width  = pDataTraining.image_width   
#image_height = pDataTraining.image_height 
#subimage_width  = pDataTraining.subimage_width   
#
#subimage_height = pDataTraining.subimage_height 
##pixelsampling_x = 2
##pixelsampling_y = 2
#pixelsampling_x = pDataTraining.pixelsampling_x 
#pixelsampling_y = pDataTraining.pixelsampling_y 
#subimage_pixelsampling=pDataTraining.subimage_pixelsampling
#subimage_first_row= pDataTraining.subimage_first_row
#subimage_first_column=pDataTraining.subimage_first_column
#add_noise_L0 = pDataTraining.add_noise_L0
#convert_format=pDataTraining.convert_format
#
##translations_x=None
##translations_y=None
#
#translations_x=pDataTraining.translations_x
#translations_y=pDataTraining.translations_y
#trans_sampled=pDataTraining.trans_sampled



#IMPROVEMENT, block_size_L0, L1, L2 should be specified just before training
#print "Using training data for slowly varying vertical angle, and (very!!!) quickly varying user identity"
#print "suggested: include_tails=False, use normal"
#image_files = []
#skip = 1
#for i in range(len(image_files1)):
#    image_files.append(image_files1[i])
#    image_files.append(image_files2[i])
#    image_files.append(image_files3[i])
#    image_files.append(image_files4[i])
#    image_files.append(image_files5[i])
#    image_files.append(image_files6[i])
#    image_files.append(image_files7[i])
#
#    
#num_images = len(image_files)
#
##block_size=num_images/5
#block_size=7
#block_size_L0=block_size
#block_size_L1=block_size
#block_size_L2=block_size
#block_size_L3=block_size
#block_size_exec=block_size #(Used only for random walk)

#Specify images to be loaded
#IMPROVEMENT: implement with a dictionary

#im_seq_base_dir = "/local/tmp/escalafl/Alberto/Renderings20x500"
#ids=range(0,8)
#expressions=[0]
#morphs=[0]
#poses=range(0,500)
#lightings=[0]
#slow_signal=0
#step=2
#offset=0
#
#image_files_training = create_image_filenames(im_seq_base_dir, slow_signal, ids, expressions, morphs, poses, lightings, step, offset)


#    print "Shape of lat_mat_L0 is:", La.lat_mat
#Create L%d sfa node
#sfa_out_dim_La = 12
#pca_out_dim_La = 90
#pca_out_dim_La = sfa_out_dim_L0 x_field_channels_La * x_field_channels_La * 0.75 


##pca_node_L3 = mdp.nodes.WhiteningNode(output_dim=pca_out_dim_L3) 
#pca_node_L3 = mdp.nodes.SFANode(output_dim=pca_out_dim_L3, block_size=block_size_L3) 
#
#exp_node_L3 = GeneralExpansionNode(exp_funcs_L3, use_hint=True, max_steady_factor=0.35, \
#                 delta_factor=0.6, min_delta=0.0001)
##exp_out_dim_L3 = exp_node_L3.output_dim
##red_node_L3 = mdp.nodes.WhiteningNode(input_dim=exp_out_dim_L3, output_dim=red_out_dim_L3)   
#red_node_L3 = mdp.nodes.WhiteningNode(output_dim=red_out_dim_L3)   
#
##sfa_node_L3 = mdp.nodes.SFANode(input_dim=preserve_mask_L2.size, output_dim=sfa_out_dim_L3)
##sfa_node_L3 = mdp.nodes.SFANode()
#sfa_node_L3 = mdp.nodes.SFANode(output_dim=sfa_out_dim_L3, block_size=block_size_L3)
#
#t8 = time.time()


#x_field_channels_L0=5
#y_field_channels_L0=5
#x_field_spacing_L0=5
#y_field_spacing_L0=5
#in_channel_dim_L0=1

#    La.v1 = (La.x_field_spacing, 0)
#    La.v2 = (La.x_field_spacing, La.y_field_spacing)
#
#    La.preserve_mask = numpy.ones((La.y_field_channels, La.x_field_channels)) > 0.5
## 6 x 12
#print "About to create (lattice based) perceptive field of width=%d, height=%d"%(La.x_field_channels, La.y_field_channels) 
#print "With a spacing of horiz=%d, vert=%d, and %d channels"%(La.x_field_spacing, La.y_field_spacing, La.in_channel_dim)
#
#(mat_connections_L0, lat_mat_L0) = compute_lattice_matrix_connections(v1_L0, v2_L0, preserve_mask_L0, subimage_width, subimage_height, in_channel_dim_L0)
#print "matrix connections L0:"
#print mat_connections_L0
#
#t1 = time.time()
#
#switchboard_L0 = PInvSwitchboard(subimage_width * subimage_height, mat_connections_L0)
#switchboard_L0.connections
#
#t2 = time.time()
#print "PInvSwitchboard L0 created in %0.3f ms"% ((t2-t1)*1000.0)
#
##Create single PCA Node
##pca_out_dim_L0 = 20
#num_nodes_RED_L0 = num_nodes_EXP_L0 = num_nodes_SFA_L0 = num_nodes_PCA_L0 = lat_mat_L0.size / 2
#
##pca_out_dim_L0 = 7
##exp_funcs_L0 = [identity, pair_prod_ex, pair_prod_adj1_ex, pair_prod_adj2_ex, pair_sqrt_abs_dif_adj2_ex]
##red_out_dim_L0 = 25
##sfa_out_dim_L0 = 20
##MEGAWARNING!!!
##pca_out_dim_L0 = 10
#
#pca_out_dim_L0 = pSFALayerL0.pca_out_dim
#exp_funcs_L0 = pSFALayerL0.exp_funcs
#red_out_dim_L0 = pSFALayerL0.red_out_dim
#sfa_out_dim_L0 = pSFALayerL0.sfa_out_dim
#
##pca_out_dim_L0 = 16
##
##exp_funcs_L0 = [identity,]
##red_out_dim_L0 = 0.99
##sfa_out_dim_L0 = 15
#
##WARNING!!!!!!!!!!!
##pca_node_L0 = mdp.nodes.WhiteningNode(input_dim=preserve_mask_L0.size, output_dim=pca_out_dim_L0)
##pca_node_L0 = mdp.nodes.SFANode(input_dim=preserve_mask_L0.size, output_dim=pca_out_dim_L0, block_size=block_size_L0)
#pca_node_L0 = pSFALayerL0.pca_node(output_dim=pca_out_dim_L0, **pSFALayerL0.pca_args)
##pca_node_L0 = mdp.nodes.WhiteningNode(output_dim=pca_out_dim_L0)
##Create array of pca_nodes (just one node, but cloned)
#pca_layer_L0 = mdp.hinet.CloneLayer(pca_node_L0, n_nodes=num_nodes_PCA_L0)
#
##exp_funcs_L0 = [identity, pair_prod_ex, pair_sqrt_abs_dif_ex, pair_sqrt_abs_sum_ex]
##exp_node_L0 = GeneralExpansionNode(exp_funcs_L0, input_dim = pca_out_dim_L0, use_hint=True, max_steady_factor=0.25, \
#exp_node_L0 = GeneralExpansionNode(exp_funcs_L0, use_hint=True, max_steady_factor=0.25, \
#                 delta_factor=0.6, min_delta=0.001)
##exp_out_dim_L0 = exp_node_L0.output_dim
#exp_layer_L0 = mdp.hinet.CloneLayer(exp_node_L0, n_nodes=num_nodes_EXP_L0)
#
##Create Node for dimensionality reduction
##red_out_dim_L0 = 20.....PCANode, WhiteningNode
##red_node_L0 = mdp.nodes.PCANode(output_dim=red_out_dim_L0)
#red_node_L0 = pSFALayerL0.red_node(output_dim=red_out_dim_L0)
##Create array of red_nodes (just one node, but cloned)
#red_layer_L0 = mdp.hinet.CloneLayer(red_node_L0, n_nodes=num_nodes_RED_L0)
#
##Create single SFA Node
##Warning Signal too short!!!!!sfa_out_dim_L0 = 20
##sfa_out_dim_L0 = 10
#sfa_node_L0 = pSFALayerL0.sfa_node(output_dim=sfa_out_dim_L0, block_size=block_size_L0)
##Create array of sfa_nodes (just one node, but cloned)
#num_nodes_SFA_L0 = lat_mat_L0.size / 2
#sfa_layer_L0 = mdp.hinet.CloneLayer(sfa_node_L0, n_nodes=num_nodes_SFA_L0)
#
#t3 = time.time()

#from experiment_datasets import pSFALayerL1 as L1
#
##Create Switchboard L1
##Create L1 sfa node
##x_field_channels_L1 = pSFALayerL1.x_field_channels
##y_field_channels_L1 = pSFALayerL1.y_field_channels
##x_field_spacing_L1 = pSFALayerL1.x_field_spacing
##y_field_spacing_L1 = pSFALayerL1.y_field_spacing
##in_channel_dim_L1 = pSFALayerL1.in_channel_dim
##
##pca_out_dim_L1 = pSFALayerL1.pca_out_dim 
##exp_funcs_L1 = pSFALayerL1.exp_funcs 
##red_out_dim_L1 = pSFALayerL1.red_out_dim 
##sfa_out_dim_L1 = pSFALayerL1.sfa_out_dim
##cloneLayerL1 = pSFALayerL1.cloneLayer
#
#L1.v1 = [L1.x_field_spacing, 0]
#L1.v2 = [L1.x_field_spacing, L1.y_field_spacing]
#
#L1.preserve_mask = numpy.ones((L1.y_field_channels, L1.x_field_channels, L1.in_channel_dim)) > 0.5
#
#print "About to create (lattice based) intermediate layer width=%d, height=%d"%(L1.x_field_channels, L1.y_field_channels) 
#print "With a spacing of horiz=%d, vert=%d, and %d channels"%(L1.x_field_spacing, L1.y_field_spacing, L1.in_channel_dim)
#
#print "Shape of lat_mat_L0 is:", lat_mat_L0
#L1.y_in_channels, L1.x_in_channels, tmp = lat_mat_L0.shape
#
##remember, here tmp is always two!!!
#
##switchboard_L1 = mdp.hinet.Rectangular2dSwitchboard(12, 6, x_field_channels_L1,y_field_channels_L1,x_field_spacing_L1,y_field_spacing_L1,in_channel_dim_L1)
#
##preserve_mask_L1_3D = wider(preserve_mask_L1, scale_x=in_channel_dim)
#(L1.mat_connections, L1.lat_mat) = compute_lattice_matrix_connections_with_input_dim(L1.v1, L1.v2, L1.preserve_mask, L1.x_in_channels, L1.y_in_channels, L1.in_channel_dim)
#print "matrix connections L1:"
#print L1.mat_connections
#L1.switchboard = PInvSwitchboard(L1.x_in_channels * L1.y_in_channels * L1.in_channel_dim, L1.mat_connections)
#
#L1.switchboard.connections
#
#t4 = time.time()
#
#L1.num_nodes = L1.lat_mat.size / 2
#
#
##Create L1 sfa node
##sfa_out_dim_L1 = 12
##pca_out_dim_L1 = 90
##pca_out_dim_L1 = sfa_out_dim_L0 x_field_channels_L1 * x_field_channels_L1 * 0.75 
#
##MEGAWARNING, "is" is a wrong condition!!!
#if L1.cloneLayer == True:
#    print "Layer L1 with ", L1.num_nodes, " cloned PCA nodes will be created"
#    print "Warning!!! layer L1 using cloned PCA instead of several independent copies!!!"
#    L1.pca_node = L1.pca_node_class(input_dim=L1.preserve_mask.size, output_dim=L1.pca_out_dim, **L1.pca_args)
#    #Create array of sfa_nodes (just one node, but cloned)
#    L1.pca_layer = mdp.hinet.CloneLayer(L1.pca_node, n_nodes=L1.num_nodes)
#else:
#    print "Layer L1 with ", L1.num_nodes, " independent PCA nodes will be created"
#    L1.PCA_nodes = range(L1.num_nodes_PCA)
#    for i in range(L1.num_nodes_PCA):
#        L1.PCA_nodes[i] = L1.pca_node_class(input_dim=L1.preserve_mask.size, output_dim=L1.pca_out_dim, **L1.pca_args)
#    L1.pca_layer_L1 = mdp.hinet.Layer(L1.PCA_nodes, homogeneous = True)
#
#L1.exp_node = GeneralExpansionNode(L1.exp_funcs, use_hint=True, max_steady_factor=0.05, \
#                 delta_factor=0.6, min_delta=0.0001)
##exp_out_dim_L1 = exp_node_L1.output_dim
#L1.exp_layer = mdp.hinet.CloneLayer(L1.exp_node, n_nodes=L1.num_nodes)
#
#if L1.cloneLayer == True: 
#    print "Warning!!! layer L1 using cloned RED instead of several independent copies!!!"
#    L1.red_node = L1.red_node_class(output_dim=L1.red_out_dim)   
#    L1.red_layer = mdp.hinet.CloneLayer(L1.red_node, n_nodes=L1.num_nodes)
#else:    
#    print "Layer L1 with ", L1.num_nodes, " independent RED nodes will be created"
#    L1.RED_nodes = range(L1.num_nodes)
#    for i in range(L1.num_nodes):
#        L1.RED_nodes[i] = L1.red_node_class(output_dim=L1.red_out_dim)
#    L1.red_layer = mdp.hinet.Layer(L1.RED_nodes, homogeneous = True)
#
#if L1.cloneLayer == True: 
#    print "Warning!!! layer L1 using cloned SFA instead of several independent copies!!!"
#    #sfa_node_L1 = mdp.nodes.SFANode(input_dim=switchboard_L1.out_channel_dim, output_dim=sfa_out_dim_L1)
#    L1.sfa_node = L1.sfa_node_class(output_dim=L1.sfa_out_dim, block_size=block_size)    
#    #!!!no ma, ya aniadele el atributo output_channels al PINVSwitchboard    
#    L1.sfa_layer = mdp.hinet.CloneLayer(L1.sfa_node, n_nodes=L1.num_nodes)
#else:    
#    print "Layer L1 with ", L1.num_nodes, " independent SFA nodes will be created"
#    L1.SFA_nodes = range(L1.num_nodes)
#    for i in range(L1.num_nodes):
#        L1.SFA_nodes[i] = L1.sfa_node_class(output_dim=L1.sfa_out_dim, block_size=block_size)
#    L1.sfa_layer = mdp.hinet.Layer(L1.SFA_nodes, homogeneous = True)

#t5 = time.time()
#
#print "LAYER L2"
##Create Switchboard L2
#x_field_channels_L2=3
#y_field_channels_L2=3
#x_field_spacing_L2=3
#y_field_spacing_L2=3
#in_channel_dim_L2=L1.sfa_out_dim
#
#v1_L2 = [x_field_spacing_L2, 0]
#v2_L2 = [x_field_spacing_L2, y_field_spacing_L2]
#
#preserve_mask_L2 = numpy.ones((y_field_channels_L2, x_field_channels_L2, in_channel_dim_L2)) > 0.5
#
#print "About to create (lattice based) third layer (L2) width=%d, height=%d"%(x_field_channels_L2,y_field_channels_L2) 
#print "With a spacing of horiz=%d, vert=%d, and %d channels"%(x_field_spacing_L2,y_field_spacing_L2,in_channel_dim_L2)
#
#print "Shape of lat_mat_L1 is:", L1.lat_mat
#y_in_channels_L2, x_in_channels_L2, tmp = L1.lat_mat.shape
#
##preserve_mask_L2_3D = wider(preserve_mask_L2, scale_x=in_channel_dim)
#(mat_connections_L2, lat_mat_L2) = compute_lattice_matrix_connections_with_input_dim(v1_L2, v2_L2, preserve_mask_L2, x_in_channels_L2, y_in_channels_L2, in_channel_dim_L2)
#print "matrix connections L2:"
#print mat_connections_L2
#switchboard_L2 = PInvSwitchboard(x_in_channels_L2 * y_in_channels_L2 * in_channel_dim_L2, mat_connections_L2)
#
#switchboard_L2.connections
#
#t6 = time.time()
#print "PinvSwitchboard L2 created in %0.3f ms"% ((t6-t5)*1000.0)
#num_nodes_PCA_L2 = num_nodes_EXP_L2 = num_nodes_RED_L2 = num_nodes_SFA_L2 = lat_mat_L2.size / 2
#
##Default: cloneLayerL2 = False
#cloneLayerL2 = False
#
##Create L2 sfa node
##sfa_out_dim_L2 = 12
##pca_out_dim_L2 = 120
#pca_out_dim_L2 = 100 
#exp_funcs_L2 = [identity,]
#red_out_dim_L2 = 100
#sfa_out_dim_L2 = 40
#
#if cloneLayerL2 == True:
#    print "Layer L2 with ", num_nodes_PCA_L2, " cloned PCA nodes will be created"
#    print "Warning!!! layer L2 using cloned PCA instead of several independent copies!!!"  
#    
#    pca_node_L2 = mdp.nodes.PCANode(input_dim=preserve_mask_L2.size, output_dim=pca_out_dim_L2)
#    #Create array of sfa_nodes (just one node, but cloned)
#    pca_layer_L2 = mdp.hinet.CloneLayer(pca_node_L2, n_nodes=num_nodes_PCA_L2)
#else:
#    print "Layer L2 with ", num_nodes_PCA_L2, " independent PCA nodes will be created"
#    PCA_nodes_L2 = range(num_nodes_PCA_L2)
#    for i in range(num_nodes_PCA_L2):
#        PCA_nodes_L2[i] = mdp.nodes.PCANode(input_dim=preserve_mask_L2.size, output_dim=pca_out_dim_L2)
#    pca_layer_L2 = mdp.hinet.Layer(PCA_nodes_L2, homogeneous = True)
#
#exp_node_L2 = GeneralExpansionNode(exp_funcs_L2, use_hint=True, max_steady_factor=0.05, \
#                 delta_factor=0.6, min_delta=0.0001)
#exp_out_dim_L2 = exp_node_L2.output_dim
#exp_layer_L2 = mdp.hinet.CloneLayer(exp_node_L2, n_nodes=num_nodes_EXP_L2)
#
#if cloneLayerL2 == True: 
#    print "Warning!!! layer L2 using cloned RED instead of several independent copies!!!"
#    red_node_L2 = mdp.nodes.WhiteningNode(output_dim=red_out_dim_L2)   
#    red_layer_L2 = mdp.hinet.CloneLayer(red_node_L2, n_nodes=num_nodes_RED_L2)
#else:    
#    print "Layer L2 with ", num_nodes_RED_L2, " independent RED nodes will be created"
#    RED_nodes_L2 = range(num_nodes_RED_L2)
#    for i in range(num_nodes_RED_L2):
#        RED_nodes_L2[i] = mdp.nodes.WhiteningNode(output_dim=red_out_dim_L2)
#    red_layer_L2 = mdp.hinet.Layer(RED_nodes_L2, homogeneous = True)
#
#if cloneLayerL2 == True:
#    print "Layer L2 with ", num_nodes_SFA_L2, " cloned SFA nodes will be created"
#    print "Warning!!! layer L2 using cloned SFA instead of several independent copies!!!"      
#    #sfa_node_L2 = mdp.nodes.SFANode(input_dim=switchboard_L2.out_channel_dim, output_dim=sfa_out_dim_L2)
#    sfa_node_L2 = mdp.nodes.SFANode(input_dim=red_out_dim_L2, output_dim=sfa_out_dim_L2, block_size=block_size_L2)
#    #!!!no ma, ya aniadele el atributo output_channels al PINVSwitchboard
#    sfa_layer_L2 = mdp.hinet.CloneLayer(sfa_node_L2, n_nodes=num_nodes_SFA_L2)
#else:
#    print "Layer L2 with ", num_nodes_SFA_L2, " independent PCA/SFA nodes will be created"
#
#    SFA_nodes_L2 = range(num_nodes_SFA_L2)
#    for i in range(num_nodes_SFA_L2):
#        SFA_nodes_L2[i] = mdp.nodes.SFANode(input_dim=red_out_dim_L2, output_dim=sfa_out_dim_L2, block_size=block_size_L2)
#    sfa_layer_L2 = mdp.hinet.Layer(SFA_nodes_L2, homogeneous = True)
#
#t7 = time.time()
#
##Create L3 sfa node
##sfa_out_dim_L3 = 150
##sfa_out_dim_L3 = 78
##WARNING!!! CHANGED PCA TO SFA
##pca_out_dim_L3 = 210
##pca_out_dim_L3 = 0.999
#pca_out_dim_L3 = 300
##exp_funcs_L3 = [identity, pair_prod_ex, pair_prod_adj1_ex, pair_prod_adj2_ex, pair_prod_adj3_ex]
#exp_funcs_L3 = [identity]
#red_out_dim_L3 = 0.999999
#sfa_out_dim_L3 = 40
#
#print "Creating final EXP/DimRed/SFA node L3"
#
##pca_node_L3 = mdp.nodes.WhiteningNode(output_dim=pca_out_dim_L3) 
#pca_node_L3 = mdp.nodes.SFANode(output_dim=pca_out_dim_L3, block_size=block_size_L3) 
#
#exp_node_L3 = GeneralExpansionNode(exp_funcs_L3, use_hint=True, max_steady_factor=0.35, \
#                 delta_factor=0.6, min_delta=0.0001)
##exp_out_dim_L3 = exp_node_L3.output_dim
##red_node_L3 = mdp.nodes.WhiteningNode(input_dim=exp_out_dim_L3, output_dim=red_out_dim_L3)   
#red_node_L3 = mdp.nodes.WhiteningNode(output_dim=red_out_dim_L3)   
#
##sfa_node_L3 = mdp.nodes.SFANode(input_dim=preserve_mask_L2.size, output_dim=sfa_out_dim_L3)
##sfa_node_L3 = mdp.nodes.SFANode()
#sfa_node_L3 = mdp.nodes.SFANode(output_dim=sfa_out_dim_L3, block_size=block_size_L3)
#
#t8 = time.time()

#Join Switchboard and SFA layer in a single flow
#flow = mdp.Flow([switchboard_L0, sfa_layer_L0, switchboard_L1, sfa_layer_L1, switchboard_L2, sfa_layer_L2, sfa_node_L3], verbose=True)
#flow = mdp.Flow([switchboard_L0, pca_layer_L0, exp_layer_L0, red_layer_L0, sfa_layer_L0, switchboard_L1, pca_layer_L1, exp_layer_L1, red_layer_L1, sfa_layer_L1, switchboard_L2, pca_layer_L2, exp_layer_L2, red_layer_L2, sfa_layer_L2, pca_node_L3, exp_node_L3, red_node_L3, sfa_node_L3], verbose=True)


#pFSeenid = ParamsInput()
#pFSeenid.name = "Gender60x200"
#pFSeenid.data_base_dir ="/local/tmp/escalafl/Alberto/RenderingsGender60x200"
#pFSeenid.ids = range(160,200)
#pFSeenid.ages = [999]
#pFSeenid.MIN_GENDER = -3
#pFSeenid.MAX_GENDER = 3
#pFSeenid.GENDER_STEP = 0.10000 #01. default. 0.4 fails, use 0.4005, 0.80075, 0.9005
##pFSeenid.GENDER_STEP = 0.80075 #01. default. 0.4 fails, use 0.4005, 0.80075, 0.9005
#pFSeenid.genders = map(code_gender, numpy.arange(pFSeenid.MIN_GENDER, pFSeenid.MAX_GENDER, pFSeenid.GENDER_STEP))
#pFSeenid.racetweens = [999]
#pFSeenid.expressions = [0]
#pFSeenid.morphs = [0]
#pFSeenid.poses = [0]
#pFSeenid.lightings = [0]
#pFSeenid.slow_signal = 2
#pFSeenid.step = 1
#pFSeenid.offset = 0                             

#im_seq_base_dir = pFSeenid.data_base_dir
#ids = pFSeenid.ids
#ages = pFSeenid.ages
#MIN_GENDER_SEENID = pFSeenid.MIN_GENDER
#MAX_GENDER_SEENID = pFSeenid.MAX_GENDER
#GENDER_STEP_SEENID = pFSeenid.GENDER_STEP
#genders = map(code_gender, numpy.arange(MIN_GENDER_SEENID, MAX_GENDER_SEENID,GENDER_STEP_SEENID))
#racetweens = pFSeenid.racetweens
#expressions = pFSeenid.expressions 
#morphs = pFSeenid.morphs 
#poses = pFSeenid.poses
#lightings = pFSeenid.lightings
#slow_signal = pFSeenid.slow_signal
#step = pFSeenid.step
#offset = pFSeenid.offset


#FOR LEARNING GENDER, INVARIANT TO IDENTITY
#im_seq_base_dir = "/local/tmp/escalafl/Alberto/RenderingsGender60x200"
#ids=range(160,200)
#ages=[999]
#GENDER_STEP_SEENID = 0.1
#genders = map(code_gender, numpy.arange(-3,3,GENDER_STEP_SEENID)) #4.005, 0.20025
#racetweens = [999]
#expressions=[0]
#morphs=[0]
#poses=[0]
#lightings=[0]
#slow_signal=2
#step=1
#offset=0

#params = [ids, expressions, morphs, poses, lightings]
#params2 = [ids, ages, genders, racetweens, expressions, morphs, poses, lightings]
#block_size_seenid= num_images_seenid / len(params2[slow_signal])

#pDataSeenid = ParamsDataLoading()
#pDataSeenid.input_files = image_files_seenid
#pDataSeenid.num_images = len(image_files_seenid)
#pDataSeenid.image_width = 256
#pDataSeenid.image_height = 192
#pDataSeenid.subimage_width = 135
#pDataSeenid.subimage_height = 135 
#pDataSeenid.pixelsampling_x = 1
#pDataSeenid.pixelsampling_y =  1
#pDataSeenid.subimage_pixelsampling = 2
#pDataSeenid.subimage_first_row =  pDataSeenid.image_height/2-pDataSeenid.subimage_height*pDataSeenid.pixelsampling_y/2
#pDataSeenid.subimage_first_column = pDataSeenid.image_width/2-pDataSeenid.subimage_width*pDataSeenid.pixelsampling_x/2+ 5*pDataSeenid.pixelsampling_x
#pDataSeenid.add_noise_L0 = True
#pDataSeenid.convert_format = "L"
#pDataSeenid.translation = 0
#pDataSeenid.translations_x = numpy.random.random_integers(-pDataSeenid.translation, pDataSeenid.translation, pDataSeenid.num_images)
#pDataSeenid.translations_y = numpy.random.random_integers(-pDataSeenid.translation, pDataSeenid.translation, pDataSeenid.num_images)
#pDataSeenid.trans_sampled = True

#image_width  = pDataSeenid.image_width   
#image_height = pDataSeenid.image_height 
#subimage_width  = pDataSeenid.subimage_width   
#subimage_height = pDataSeenid.subimage_height 
#pixelsampling_x = pDataSeenid.pixelsampling_x 
#pixelsampling_y = pDataSeenid.pixelsampling_y 
#subimage_pixelsampling=pDataSeenid.subimage_pixelsampling
#subimage_first_row= pDataSeenid.subimage_first_row
#subimage_first_column=pDataSeenid.subimage_first_column
#add_noise_L0 = pDataSeenid.add_noise_L0
#convert_format=pDataSeenid.convert_format
#translations_x=pDataSeenid.translations_x
#translations_y=pDataSeenid.translations_y
#trans_sampled=pDataSeenid.trans_sampled

##image_width  = 640
##image_height = 480
#image_width  = 256
#image_height = 192
#subimage_width  = 135
#subimage_height = 135 
#pixelsampling_x = 1
#pixelsampling_y = 1
#subimage_pixelsampling=1
##pixelsampling_x = 2
##pixelsampling_y = 2
##subimage_pixelsampling=2
#subimage_first_row= image_height/2-subimage_height*pixelsampling_y/2
#subimage_first_column=image_width/2-subimage_width*pixelsampling_x/2+ 5*pixelsampling_x
#add_noise_L0 = False
#convert_format="L"
#translations_x=numpy.random.random_integers(-translation, translation, num_images_seenid) 
#translations_y=numpy.random.random_integers(-translation, translation, num_images_seenid)
#trans_sampled=True


#image_files_seenid = create_image_filenames2(im_seq_base_dir, slow_signal, ids, ages, genders, racetweens, \
#                            expressions, morphs, poses, lightings, step, offset)
#
#num_images_seenid = len(image_files_seenid)
#
#subimages_seenid = load_image_data(image_files_seenid, image_width, image_height, subimage_width, subimage_height, \
#                    pixelsampling_x, pixelsampling_y, subimage_first_row, subimage_first_column, \
#                    add_noise_L0, convert_format, translations_x, translations_y, trans_sampled)


#pFNewid = ParamsInput()
#pFNewid.name = "Gender60x200"
#pFNewid.data_base_dir ="/local/tmp/escalafl/Alberto/Renderings20x500"
#pFNewid.ids = range(0,2)
#pFNewid.ages = [999]
#pFNewid.MIN_GENDER = -3
#pFNewid.MAX_GENDER = 3
#pFNewid.GENDER_STEP = 0.10000 #01. default. 0.4 fails, use 0.4005, 0.80075, 0.9005
##pFNewid.GENDER_STEP = 0.80075 #01. default. 0.4 fails, use 0.4005, 0.80075, 0.9005
#pFNewid.genders = map(code_gender, numpy.arange(pFNewid.MIN_GENDER, pFNewid.MAX_GENDER, pFNewid.GENDER_STEP))
#pFNewid.racetweens = [999]
#pFNewid.expressions = [0]
#pFNewid.morphs = [0]
#pFNewid.poses = range(0,500)
#pFNewid.lightings = [0]
#pFNewid.slow_signal = 0
#pFNewid.step = 4
#pFNewid.offset = 0                             
#
#im_seq_base_dir = pFNewid.data_base_dir
#ids = pFNewid.ids
#ages = pFNewid.ages
#MIN_GENDER_NEWID = pFNewid.MIN_GENDER
#MAX_GENDER_NEWID = pFNewid.MAX_GENDER
#GENDER_STEP_NEWID = pFNewid.GENDER_STEP
#genders = map(code_gender, numpy.arange(MIN_GENDER_NEWID , MAX_GENDER_NEWID ,GENDER_STEP_NEWID ))
#racetweens = pFNewid.racetweens
#expressions = pFNewid.expressions 
#morphs = pFNewid.morphs 
#poses = pFNewid.poses
#lightings = pFNewid.lightings
#slow_signal = pFNewid.slow_signal
#step = pFNewid.step
#offset = pFNewid.offset
#
###im_seq_base_dir = "/local/tmp/escalafl/Alberto/testing_newid"
##im_seq_base_dir = "/local/tmp/escalafl/Alberto/Renderings20x500"
##ids=range(0,2)
##expressions=[0]
##morphs=[0]
##poses=range(0,500)
##lightings=[0]
##slow_signal=0
##step=4
##offset=0
#
#image_files_newid = create_image_filenames(im_seq_base_dir, slow_signal, ids, expressions, morphs, poses, lightings, step, offset)
#num_images_newid = len(image_files_newid)
#params = [ids, expressions, morphs, poses, lightings]
#block_size_newid= num_images_newid / len(params[slow_signal])
#
#
#
#
##image_width  = 640
##image_height = 480subimages_seenid
##subimage_width  = 135
##subimage_height = 135 
##pixelsampling_x = 2
##pixelsampling_y = 2
##subimage_pixelsampling=2
##subimage_first_row= image_height/2-subimage_height*pixelsampling_y/2
##subimage_first_column=image_width/2-subimage_width*pixelsampling_x/2+ 5*pixelsampling_x
##add_noise_L0 = False
##convert_format="L"
##translations_x=None
##translations_y=None
##trans_sampled=True
#
#
#pDataNewid = ParamsDataLoading()
#pDataNewid.input_files = image_files_seenid
#pDataNewid.num_images = len(image_files_seenid)
#pDataNewid.image_width = 640
#pDataNewid.image_height = 480
#pDataNewid.subimage_width = 135
#pDataNewid.subimage_height = 135 
#pDataNewid.pixelsampling_x = 2
#pDataNewid.pixelsampling_y =  2
#pDataNewid.subimage_pixelsampling = 2
#pDataNewid.subimage_first_row =  pDataNewid.image_height/2-pDataNewid.subimage_height*pDataNewid.pixelsampling_y/2
#pDataNewid.subimage_first_column = pDataNewid.image_width/2-pDataNewid.subimage_width*pDataNewid.pixelsampling_x/2+ 5*pDataNewid.pixelsampling_x
#pDataNewid.add_noise_L0 = False
#pDataNewid.convert_format = "L"
#pDataNewid.translation = 0
#pDataNewid.translations_x = numpy.random.random_integers(-pDataNewid.translation, pDataNewid.translation, pDataNewid.num_images)
#pDataNewid.translations_y = numpy.random.random_integers(-pDataNewid.translation, pDataNewid.translation, pDataNewid.num_images)
#pDataNewid.trans_sampled = True
#
#image_width  = pDataNewid.image_width   
#image_height = pDataNewid.image_height 
#subimage_width  = pDataNewid.subimage_width   
#subimage_height = pDataNewid.subimage_height 
#pixelsampling_x = pDataNewid.pixelsampling_x 
#pixelsampling_y = pDataNewid.pixelsampling_y 
#subimage_pixelsampling=pDataNewid.subimage_pixelsampling
#subimage_first_row= pDataNewid.subimage_first_row
#subimage_first_column=pDataNewid.subimage_first_column
#add_noise_L0 = pDataNewid.add_noise_L0
#convert_format=pDataNewid.convert_format
#translations_x=pDataNewid.translations_x
#translations_y=pDataNewid.translations_y
#trans_sampled=pDataNewid.trans_sampled
#
#subimages_newid = load_image_data(image_files_newid, image_width, image_height, subimage_width, subimage_height, \
#                    pixelsampling_x, pixelsampling_y, subimage_first_row, subimage_first_column, \
#                    add_noise_L0, convert_format, translations_x, translations_y, trans_sampled)

##Testing hash function
##print "Testing for bug in hashing of RandomPermutationNode..."
##xx = numpy.array([[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]])
##node1 = more_nodes.RandomPermutationNode()
##node1.train(xx)
##node2 = more_nodes.RandomPermutationNode()
##node2.train(xx)
##
##hash1 = cache.hash_object(node1, m=None, recursion=True, verbose=False)
##hash2 = cache.hash_object(node2, m=None, recursion=True, verbose=False)
##
##print "hash1=", hash1.hexdigest()
##print "hash2=", hash2.hexdigest()
##print "hash values should usually differ since there are two trainings"
##print "*********************************************************************"
##
##print "Testing for bug in hashing of RandomPermutationNode..."
##xx = numpy.array([[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]])
##node1 = more_nodes.GeneralExpansionNode([identity])
##node2 = more_nodes.GeneralExpansionNode([pair_prod_adj2_ex])
##
##hash1 = cache.hash_object(node1, m=None, recursion=True, verbose=False)
##hash2 = cache.hash_object(node2, m=None, recursion=True, verbose=False)
##
##print "hash1=", hash1.hexdigest()
##print "hash2=", hash2.hexdigest()
##print "hash values should be equal if expansion functions are the same"
##print "*********************************************************************"
##
##quit()
