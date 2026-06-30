import numpy as np
import xarray as xr


def apply_qc(ds: xr.Dataset, var: str) -> xr.DataArray:
    """
    Apply QC masking to a variable in an xarray Dataset.

    Replaces FillValue, out-of-range, and bad-flag cells with NaN.

    Parameters:
    -----------
    ds : xr.Dataset
        Input dataset containing the variable
    var : str
        Variable name to apply QC to

    Returns:
    --------
    xr.DataArray
        QC-masked data array with NaN values replacing invalid cells

    Raises:
    -------
    KeyError
        If variable not found in dataset
    """
    if var not in ds:
        available = list(ds.data_vars)
        raise KeyError(
            f"변수 '{var}' 없음. 파일 내 변수: {available}"
        )

    da = ds[var].astype(float)
    attrs = da.attrs

    # Step 1: Replace FillValue with NaN
    fill = attrs.get("_FillValue", attrs.get("missing_value", None))
    if fill is not None:
        da = da.where(da != fill)

    # Step 2: Apply valid_range or valid_min/valid_max
    vmin = attrs.get("valid_min", None)
    vmax = attrs.get("valid_max", None)
    if "valid_range" in attrs:
        vmin, vmax = attrs["valid_range"][0], attrs["valid_range"][1]
    if vmin is not None:
        da = da.where(da >= float(vmin))
    if vmax is not None:
        da = da.where(da <= float(vmax))

    # Step 3: Apply flag masking (ancillary_variables)
    flag_var = attrs.get("ancillary_variables", None)
    if flag_var and flag_var in ds:
        flag_da = ds[flag_var]
        flag_attrs = flag_da.attrs
        masks = flag_attrs.get("flag_masks", None)
        meanings = flag_attrs.get("flag_meanings", "")
        if masks is not None:
            good_mask = np.zeros(flag_da.shape, dtype=bool)
            for mask_val, meaning in zip(masks, meanings.split()):
                if "good" in meaning.lower():
                    good_mask |= (flag_da.values & mask_val).astype(bool)
            da = da.where(good_mask)

    return da
