from app.services.chord_shapes import chord_shape
from app.services.music_theory import Chord
from fastapi import APIRouter, HTTPException, Query, status

router = APIRouter(prefix="/api/chords", tags=["chords"])


@router.get("")
async def get_chord_shape(chord: str = Query(..., min_length=1, max_length=32)):
    """The server's open-position shape for one chord (#142)."""
    try:
        parsed = Chord.parse(chord)
    except (KeyError, IndexError, ValueError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown chord"
        ) from e
    frets = chord_shape(parsed)
    if frets is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No diagram for this chord",
        )
    return {"name": str(parsed), "frets": frets}
