from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, model_validator


# class Img2ColmapRequest(BaseModel):
#     """
#     Request model for converting images to COLMAP format.
#     """
#     conf_threshold: Optional[float] = Field(
#         0.5,
#         description="Confidence threshold for filtering detections.",
#         ge=0.0, le=1.0,
#         examples=[0.5, 0.7]
#     )
#     mask_sky: Optional[bool] = Field(
#         False,
#         description="Whether to mask the sky in the images.",
#         examples=[True, False]
#     )
#     mask_black_bg: Optional[bool] = Field(
#         False,
#         description="Whether to mask black backgrounds in the images.",
#         examples=[True, False]
#     )
#     mask_white_bg: Optional[bool] = Field(
#         False,
#         description="Whether to mask white backgrounds in the images.",
#         examples=[True, False]
#     )
#     stride: Optional[int] = Field(
#         1,
#         description="Stride for point sampling (higher = fewer points)",
#         ge=1,
#         examples=[1, 2, 3]
#     )



