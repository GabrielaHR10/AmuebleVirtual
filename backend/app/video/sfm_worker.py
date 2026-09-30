"""SfM con pycolmap en un proceso aparte (sin PyTorch): en macOS ambos traen su propia libomp y no pueden
cargarse en el mismo proceso ("OMP: Error #15"). Uso: python -m app.video.sfm_worker <imagenes> <trabajo> <salida.json>
"""

import json
import sys
from pathlib import Path


def main(image_dir: str, work: str, out_json: str) -> None:
    import pycolmap

    work_p = Path(work)
    work_p.mkdir(parents=True, exist_ok=True)
    db = work_p / "database.db"
    db.unlink(missing_ok=True)
    reader = pycolmap.ImageReaderOptions()
    reader.camera_model = "SIMPLE_PINHOLE"
    pycolmap.extract_features(db, image_dir, camera_mode=pycolmap.CameraMode.SINGLE, reader_options=reader)
    pairing = pycolmap.SequentialPairingOptions()
    pairing.overlap = 10
    pycolmap.match_sequential(db, pairing_options=pairing)
    maps = pycolmap.incremental_mapping(db, image_dir, work_p / "sparse")
    if not maps:
        Path(out_json).write_text(json.dumps({"images": {}}))
        return
    rec = max(maps.values(), key=lambda r: r.num_reg_images())
    cams = {cid: {"width": c.width, "height": c.height, "params": list(map(float, c.params))}
            for cid, c in rec.cameras.items()}
    images = {}
    for img in rec.images.values():
        has_pose = img.has_pose() if callable(img.has_pose) else img.has_pose
        if not has_pose:
            continue
        cfw = img.cam_from_world() if callable(img.cam_from_world) else img.cam_from_world
        obs = [[*map(float, p.xy), *map(float, rec.points3D[p.point3D_id].xyz)]
               for p in img.points2D if p.has_point3D()]
        images[img.name] = {"camera_id": img.camera_id, "cam_from_world": cfw.matrix().tolist(), "obs": obs}
    Path(out_json).write_text(json.dumps({"cameras": cams, "images": images}))


if __name__ == "__main__":
    main(*sys.argv[1:4])
