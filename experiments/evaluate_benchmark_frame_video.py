from __future__ import annotations

from pathlib import Path

from ns_vfs.common.utility import save_dict_to_pickle, save_frames
from ns_vfs.config.loader import load_config
from ns_vfs.data.frame import BenchmarkLTLFrame
from ns_vfs.frame_searcher import FrameSearcher
from ns_vfs.model.vision.grounding_dino import GroundingDino
from ns_vfs.processor.benchmark_video_processor import BenchmarkVideoFrameProcessor
from ns_vfs.video_to_automaton import VideotoAutomaton


def get_frames(frames_of_interest: list, benchmark_video: BenchmarkLTLFrame):
    output = []
    for frame_set in frames_of_interest:
        if len(frame_set) == 1:
            idx = frame_set[0]
            output.append([benchmark_video.images_of_frames[idx]])
        else:
            idx_first, idx_last = frame_set[0], frame_set[-1]
            tmp_list = []
            for idx in range(idx_first, idx_last + 1):
                tmp_list.append(benchmark_video.images_of_frames[idx])
            output.append(tmp_list)
            tmp_list = []
    return output


def evaluate_frame_of_interest(
    benchmark_video_file: str,
    benchmark_video: BenchmarkLTLFrame,
    frame_of_interest: list,
    directory_path: str,
):
    result = dict()
    dir_path = Path(directory_path) / benchmark_video_file.name.split(".pkl")[0]
    dir_path.mkdir(parents=True, exist_ok=True)

    true_list = benchmark_video.frames_of_interest
    matching_sublists = sum(1 for a, b in zip(true_list, frame_of_interest) if a == b)
    total_sublists = len(true_list)
    exact_frame_accuracy = matching_sublists / total_sublists

    # matching_accuracy
    flattened_true_set = set([item for sublist in true_list for item in sublist])
    flattened_predict_set = set([item for sublist in frame_of_interest for item in sublist])
    common_elements = flattened_true_set.intersection(flattened_predict_set)
    fail_to_predict = flattened_predict_set.difference(flattened_true_set)

    # filename = benchmark_video_file.name.split("_ltl_")[-1].split("_")[0]
    dir_path / benchmark_video_file.name.split(".pkl")[0] / ".json"

    result["exact_frame_accuracy"] = exact_frame_accuracy
    result["num_true_positive"] = len(common_elements)
    result["ratio_true_positive"] = len(common_elements) / len(flattened_true_set)
    result["num_false_positive"] = len(fail_to_predict)
    result["ratio_false_positive"] = len(fail_to_predict) / len(flattened_predict_set)
    result["ltl_formula"] = benchmark_video.ltl_formula
    result["groud_truth_frame"] = benchmark_video.frames_of_interest
    result["predicted_frame"] = frame_of_interest
    result["groud_truth_img"] = get_frames(benchmark_video.frames_of_interest, benchmark_video)
    result["predicted_img"] = get_frames(frame_of_interest, benchmark_video)
    result["total_number_of_framer_of_interest"] = len(benchmark_video.frames_of_interest)
    result["total_number_of_frame"] = len(benchmark_video.labels_of_frames)

    i = 0
    for fram_img_set in result["predicted_img"]:
        path = Path(directory_path) / benchmark_video_file.name.split(".pkl")[0] / f"video_frame_{i}"
        save_frames(frames=fram_img_set, path=path, file_label="predicted_frame")
        i += 1

    save_dict_to_pickle(
        path=Path(directory_path) / benchmark_video_file.name.split(".pkl")[0],
        dict_obj=result,
        file_name="result.pkl",
    )

    acc_file = Path(directory_path) / "accuracy.txt"
    with acc_file.open("a") as f:
        f.write(
            f"""{result["ltl_formula"]} - total num frame: {result["total_number_of_frame"]} - exact_frame_accuracy: {result["exact_frame_accuracy"]} 
            num_true_positive: {result["num_true_positive"]}, ratio_true_positive: {result["ratio_true_positive"]} num_false_positive: {result["num_false_positive"]} ratio_false_positive: {result["ratio_false_positive"]}\n"""
        )


def get_available_benchmark_video(path_to_directory: str):
    if isinstance(path_to_directory, str):
        directory_path = Path(path_to_directory)
        return list(directory_path.glob("*.pkl"))
    else:
        directory_path = path_to_directory
        return list(directory_path.rglob("*.pkl"))


if __name__ == "__main__":
    config = load_config()
    benchmark_frame_video_root_dir = Path(
        "/opt/Neuro-Symbolic-Video-Frame-Search/artifacts/benchmark_frame_video/"
    )

    benchmark_image_set_dir = [x for x in benchmark_frame_video_root_dir.iterdir() if x.is_dir()]

    for benchmark_name_dir in benchmark_image_set_dir:
        ltl_video_dir_set = [x for x in benchmark_name_dir.iterdir() if x.is_dir()]
        if len(ltl_video_dir_set) > 0:
            print(f"--processing {benchmark_name_dir.name}--")
            print(f"number of ltl rule: {len(ltl_video_dir_set)}")
            for ltl_video_dir in ltl_video_dir_set:
                benchmark_video_file_list = get_available_benchmark_video(ltl_video_dir)
                print(f"number of examples of {ltl_video_dir.name}: {len(benchmark_video_file_list)}")

                for benchmark_video_file in benchmark_video_file_list:
                    benchmark_video_processor = BenchmarkVideoFrameProcessor(
                        video_path=benchmark_video_file,
                        artifact_dir=config.VERSION_AND_PATH.ARTIFACTS_PATH,
                    )

                    benchmark_img_frame: BenchmarkLTLFrame = benchmark_video_processor.benchmark_image_frames

                    video_automata_builder = VideotoAutomaton(
                        detector=GroundingDino(
                            config=config.GROUNDING_DINO,
                            weight_path=config.GROUNDING_DINO.GROUNDING_DINO_CHECKPOINT_PATH,
                            config_path=config.GROUNDING_DINO.GROUNDING_DINO_CONFIG_PATH,
                        ),
                        video_processor=benchmark_video_processor,
                        artifact_dir=config.VERSION_AND_PATH.ARTIFACTS_PATH,
                        proposition_set=benchmark_img_frame.proposition,
                        save_annotation=False,  # TODO: Debug only
                        save_image=False,  # TODO: Debug only
                        ltl_formula=f"P>=0.80 [{benchmark_img_frame.ltl_formula}]",
                        verbose=False,
                        manual_confidence_probability=1.0,
                    )
                    frame_sercher = FrameSearcher(
                        video_automata_builder=video_automata_builder,
                        video_processor=benchmark_video_processor,
                    )

                    frame_of_interest = frame_sercher.search()

                    evaluate_frame_of_interest(
                        benchmark_video_file=benchmark_video_file,
                        benchmark_video=benchmark_img_frame,
                        frame_of_interest=frame_of_interest,
                        directory_path="/opt/Neuro-Symbolic-Video-Frame-Search/artifacts/benchmark_frame_video/results",
                    )
