from __future__ import annotations

import dataclasses  # noqa: D100
import random
from pathlib import Path
from typing import Dict, List, Optional

import cv2
import numpy as np
import torch
from PIL import Image

from ns_vfs.common.frame_grouping import combine_consecutive_lists
from ns_vfs.common.utility import (
    get_file_or_dir_with_datetime,
)


@dataclasses.dataclass
class Frame:
    """Frame class."""

    frame_idx: int
    timestamp: Optional[int] = None
    frame_image: Optional[np.ndarray] = None
    annotated_image: Dict[str, np.ndarray] = dataclasses.field(
        default_factory=dict
    )
    object_of_interest: Optional[dict] = None
    activity_of_interest: Optional[dict] = None

    def is_any_object_detected(self):
        """Check if object is detected."""
        if len(self.detected_object_list) == 0:
            return False
        else:
            return True

    @property
    def detected_object_list(self):
        """Get detected object."""
        detected_obj = []
        for obj_name, obj_value in self.object_of_interest.items():
            if obj_value.is_detected:
                detected_obj.append(obj_name)
        return detected_obj

    @property
    def detected_object_dict(self):
        """Get detected object info as dict."""
        detected_obj = {}
        for obj_name, obj_value in self.object_of_interest.items():
            if obj_value.is_detected:
                detected_obj[obj_name] = {}
                detected_obj[obj_name]["total_number_of_detection"] = (
                    obj_value.number_of_detection
                )
                detected_obj[obj_name]["maximum_probability"] = max(
                    obj_value.probability_of_all_obj
                )
                detected_obj[obj_name]["minimum_probability"] = min(
                    obj_value.probability_of_all_obj
                )
                detected_obj[obj_name]["maximum_confidence"] = max(
                    obj_value.confidence_of_all_obj
                )
                detected_obj[obj_name]["minimum_confidence"] = min(
                    obj_value.confidence_of_all_obj
                )

        return detected_obj

    @property
    def detected_bboxes(self):
        """Get detected object."""
        bboxes = []
        for obj_name, obj_value in self.object_of_interest.items():
            if obj_value.is_detected:
                for obj_prob in obj_value.probability_of_all_obj:
                    if obj_prob > 0:
                        bboxes += obj_value.bounding_box_of_all_obj
        return bboxes


@dataclasses.dataclass
class FramesofInterest:
    """Frame class."""

    ltl_formula: str
    foi_list: List[List[int]] = dataclasses.field(default_factory=list)
    frame_images: List[np.ndarray] = dataclasses.field(default_factory=list)
    annotated_images: List[np.ndarray] = dataclasses.field(default_factory=list)
    frame_idx_to_real_idx: dict = dataclasses.field(default_factory=dict)
    frame_buffer: List[Frame] = dataclasses.field(default_factory=list)

    def save_annotated_images(self, annotated_image: Dict[str, np.ndarray]):
        for a_img in list(annotated_image.values()):
            self.annotated_images.append(a_img)

    def save_frames_of_interest(self, path):
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        for idx, img in enumerate(self.frame_images):
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            Image.fromarray(img_rgb).save(f"{path}/{idx}.png")
            try:
                if (
                    len(self.annotated_images) > 0
                    and self.annotated_images[idx] is not None
                ):
                    Image.fromarray(self.annotated_images[idx]).save(
                        f"{path}/{idx}_annotated.png"
                    )
            except:  # noqa: E722
                pass

    def flush_frame_buffer(self):
        """Flush frame buffer to frame of interest."""
        if len(self.frame_buffer) > 1:
            frame_interval = list()
            for frame in self.frame_buffer:
                frame_interval.append(frame.frame_idx)
                self.frame_idx_to_real_idx[frame.frame_idx] = frame.timestamp
                self.frame_images.append(frame.frame_image)
                self.save_annotated_images(frame.annotated_image)
            self.foi_list.append(frame_interval)
        else:
            for frame in self.frame_buffer:
                self.foi_list.append([frame.frame_idx])
                self.frame_idx_to_real_idx[frame.frame_idx] = frame.timestamp
                self.frame_images.append(frame.frame_image)
                self.save_annotated_images(frame.annotated_image)
        self.frame_buffer = list()

    def save(self, path: str | Path):
        from PIL import Image

        if isinstance(path, str):
            root_path = Path(path)
        else:
            root_path = path
        dir_name = get_file_or_dir_with_datetime("foi_result")
        frame_path = root_path / dir_name / "frame"
        annotation_path = root_path / dir_name / "annotation"

        frame_path.mkdir(parents=True, exist_ok=True)
        annotation_path.mkdir(parents=True, exist_ok=True)

        for idx, img in enumerate(self.frame_images):
            Image.fromarray(img).save(f"{frame_path}/{idx}.png")
            try:
                if (
                    len(self.annotated_images) > 0
                    and self.annotated_images[idx] is not None
                ):
                    Image.fromarray(self.annotated_images[idx]).save(
                        f"{annotation_path}/{idx}_annotated.png"
                    )
            except:  # noqa: E722
                pass


@dataclasses.dataclass
class BenchmarkRawImage:
    """Benchmark image frame class."""

    unique_labels: list
    labels: List[List[str]]
    images: List[np.ndarray]

    def sample_image_from_label(
        self, labels: list, proposition: list
    ) -> np.ndarray:
        """Sample image from label."""
        image_of_frame = []
        img_to_label = {}
        img_to_label_list = {}
        for prop in proposition:
            # img_to_label[prop] = [i for i, value in enumerate(self.labels) if value == prop]
            img_to_label[prop] = [
                i for i, value in enumerate(self.labels) if prop in value
            ]
        # img_to_label_list[tuple(sorted(proposition))] = [
        #     i for i, value in enumerate(self.labels) if all(prop in value for prop in proposition)
        # ]

        label_idx = 0
        for label in labels:
            if label is None:
                while True:
                    random_idx = random.randrange(
                        len(self.images)
                    )  # pick one random image with idx
                    val = []
                    for single_label in self.labels[
                        random_idx
                    ]:  # go over all labels of the image
                        if single_label in proposition:
                            val.append(True)
                    if True not in val:
                        labels[label_idx] = single_label
                        image_of_frame.append(self.images[random_idx])
                        break
            else:
                # lable available - just get the image
                if isinstance(label, str):
                    # one label in the frame
                    random_idx = random.choice(img_to_label[label])
                    # plt.imshow(self.images[random_idx])
                    # plt.axis("off")
                    # plt.savefig("data_loader_sample_image.png")
                    image_of_frame.append(self.images[random_idx])
                elif isinstance(label, list):
                    img_to_label_list[tuple(sorted(label))] = [
                        i
                        for i, value in enumerate(self.labels)
                        if all(prop in value for prop in label)
                    ]
                    random_idx = random.choice(
                        img_to_label_list[tuple(sorted(label))]
                    )
                    image_of_frame.append(self.images[random_idx])
            label_idx += 1
        return labels, image_of_frame


@dataclasses.dataclass
class BenchmarkRawImageDataset:
    """Benchmark image frame class with a torchvision dataset for large datasets."""

    unique_labels: list
    labels: List[List[str]]
    images: torch.utils.data.Dataset

    def sample_image_from_label(
        self, labels: list, proposition: list
    ) -> np.ndarray:
        """Sample image from label."""
        image_of_frame = []
        img_to_label = {}
        for prop in proposition:
            # img_to_label[prop] = [i for i, value in enumerate(self.labels) if value == prop]
            img_to_label[prop] = [
                i for i, value in enumerate(self.labels) if prop in value
            ]

        label_idx = 0
        for label in labels:
            if label is None:
                while True:
                    random_idx = random.randrange(len(self.images))
                    if self.labels[random_idx] not in proposition:
                        break
                labels[label_idx] = self.labels[random_idx]
                image_of_frame.append(self.images[random_idx][0])
            else:
                random_idx = random.choice(img_to_label[label])
                image_of_frame.append(self.images[random_idx][0])

            label_idx += 1
        return labels, image_of_frame


@dataclasses.dataclass
class BenchmarkLTLFrame:
    """Benchmark image frame class.

    ground_truth (bool): Ground truth answer of LTL condition for frames
    ltl_frame (str): LTL formula
    number_of_frame (int): Number of frame
    frames_of_interest (list): List of frames that satisfy LTL condition
    - [[0]] -> Frame 0 satisfy LTL condition;
      [[4,5,6,7]] -> Frame 4 to 7 satisfy LTL condition
      [[0],[4,5,6,7]] -> Frame 0 and Frame 4 to 7 satisfy LTL condition.
    labels_of_frame: list of labels of frame
    """

    ground_truth: bool
    ltl_formula: str
    proposition: list
    number_of_frame: int
    frames_of_interest: Optional[List[List[int]]]
    labels_of_frames: List[str]
    images_of_frames: List[np.ndarray] = dataclasses.field(default_factory=list)

    def __post_init__(self):
        """Post init."""
        self.frames_of_interest = combine_consecutive_lists(
            data=self.frames_of_interest
        )

    def save_frames(
        self, path="/opt/Neuro-Symbolic-Video-Frame-Search/artifacts"
    ) -> None:
        """Save image to path.

        Args:
        path (str, optional): Path to save image.
        """
        from PIL import Image

        for idx, img in enumerate(self.images_of_frames):
            Image.fromarray(img).save(f"{path}/{idx}.png")

    def save(
        self,
        save_path: str = "/opt/Neuro-Symbolic-Video-Frame-Search/artifacts",
    ) -> None:
        """Save the current instance to a pickle file."""
        import pickle

        """Save the current instance to a pickle file."""
        with open(save_path, "wb") as f:
            pickle.dump(self, f)
