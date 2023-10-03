from ns_vfs.generator.data_generator import BenchmarkVideoGenerator
from ns_vfs.loader.benchmark_cifar import Cifar10ImageLoader, Cifar100ImageLoader
from ns_vfs.loader.benchmark_imagenet import ImageNetDataloader

DATASET_TYPE = "cifar10"  # "cifar10" or "imagenet"

if __name__ == "__main__":
    if DATASET_TYPE == "cifar10":
        image_dir = "/opt/Neuro-Symbolic-Video-Frame-Search/artifacts/data/benchmark_image_dataset/cifar-10-batches-py"
        image_loader = Cifar10ImageLoader(cifar_dir_path=image_dir)
    elif DATASET_TYPE == "cifar100":
        image_dir = (
            "/opt/Neuro-Symbolic-Video-Frame-Search/artifacts/data/benchmark_image_dataset/cifar-100-python"
        )
        image_loader = Cifar100ImageLoader(cifar_dir_path=image_dir)
    elif DATASET_TYPE == "imagenet":
        image_dir = "/store/datasets/ILSVRC"
        image_loader = ImageNetDataloader(imagenet_dir_path=image_dir)
    video_generator = BenchmarkVideoGenerator(
        image_data_loader=image_loader,
        artificat_dir="/opt/Neuro-Symbolic-Video-Frame-Search/artifacts/benchmark_frame_video",
    )
    video_generator.generate(max_number_frame=100, ltl_logic="F prop1", save_frames=False)
    # prop1 U prop2
    # F prop1
    # G prop1
    print("Done!")
