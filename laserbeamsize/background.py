"""
Routines for removing background for beam analysis.

Full documentation is available at <https://laserbeamsize.readthedocs.io>

Two functions are used to find the mean and standard deviation of images.
`corner_background()` uses just the corner pixels and `iso_background()` uses
all un-illuminated pixels::

    >>> import imageio.v3 as iio
    >>> import laserbeamsize as lbs
    >>>
    >>> file = "https://github.com/scottprahl/laserbeamsize/raw/main/docs/t-hene.pgm"
    >>> image = iio.imread(file)
    >>>
    >>> mean, stdev = lbs.corner_background(image)
    >>> print("The corner pixels have an average         %.1f ± %.1f)" % (mean, stdev))
    >>> mean, stdev = lbs.iso_background(image)
    >>> print("The un-illuminated pixels have an average %.1f ± %.1f)" % (mean, stdev))

In addition to these functions, there are a variety of subtraction functions to
remove the background.  The most useful is `subtract_iso_background()` which will
return an image with the average of the un-illuminated pixels subtracted::

    >>> import imageio.v3 as iio
    >>> import laserbeamsize as lbs
    >>>
    >>> file = "https://github.com/scottprahl/laserbeamsize/raw/main/docs/t-hene.pgm"
    >>> image = iio.imread(file)
    >>>
    >>> clean_image = subtract_iso_background(image)

Full documentation is available at <https://laserbeamsize.readthedocs.io>
"""

import numpy as np
import scipy.ndimage

from .image_tools import rotate_image

__all__ = (
    "corner_mask",
    "perimeter_mask",
    "rotated_rect_mask",
    "elliptical_mask",
    "iso_background_mask",
    "corner_background",
    "iso_background",
    "subtract_background_image",
    "subtract_constant",
    "subtract_corner_background",
    "subtract_iso_background",
    "subtract_tilted_background",
)


def elliptical_mask(image, xc, yc, d_major, d_minor, phi):
    """
    Create a boolean mask for a rotated elliptical disk.

    The returned mask is the same size as `image`.

    Args:
        image: 2D array
        xc: horizontal center of beam
        yc: vertical center of beam
        d_major: semi-major ellipse diameter
        d_minor: semi-minor ellipse diameter
        phi: angle between horizontal and major axes [radians]

    Returns:
        masked_image: 2D array with True values inside ellipse
    """
    v, h = image.shape
    y, x = np.ogrid[:v, :h]

    sinphi = np.sin(phi)
    cosphi = np.cos(phi)
    rx = d_major / 2
    ry = d_minor / 2
    xx = x - xc
    yy = y - yc
    r2 = (xx * cosphi - yy * sinphi) ** 2 / rx**2 + (xx * sinphi + yy * cosphi) ** 2 / ry**2
    the_mask = r2 <= 1

    return the_mask


def corner_mask(image, corner_fraction=0.035):
    """
    Create boolean mask for image with corners marked as True.

    Each of the four corners is a fixed percentage of the entire image.

    ISO 11146-3 recommends values from 2-5% for `corner_fraction`
    the default is 0.035=3.5% of the iamge.

    Args:
        image : the image to work with
        corner_fraction: the fractional size of corner rectangles
    Returns:
        masked_image: 2D array with True values in four corners
    """
    v, h = image.shape
    n = int(v * corner_fraction)
    m = int(h * corner_fraction)

    the_mask = np.full_like(image, False, dtype=bool)
    the_mask[:n, :m] = True
    the_mask[:n, -m:] = True
    the_mask[-n:, :m] = True
    the_mask[-n:, -m:] = True
    return the_mask


def perimeter_mask(image, corner_fraction=0.035):
    """
    Create boolean mask for image with a perimeter marked as True.

    The perimeter is the same width as the corners created by corner_mask
    which is a fixed percentage (default 3.5%) of the entire image.

    Args:
        image : the image to work with
        corner_fraction: determines the width of the perimeter
    Returns:
        masked_image: 2D array with True values around rect perimeter
    """
    v, h = image.shape
    n = int(v * corner_fraction)
    m = int(h * corner_fraction)

    the_mask = np.full_like(image, False, dtype=bool)
    the_mask[:, :m] = True
    the_mask[:, -m:] = True
    the_mask[:n, :] = True
    the_mask[-n:, :] = True
    return the_mask


def rotated_rect_mask_slow(image, xc, yc, d_major, d_minor, phi, mask_diameters=3):
    """
    Create ISO 11146 rectangular mask for specified beam.

    ISO 11146-2 §7.2 states that integration should be carried out over
    "a rectangular integration area which is centred to the beam centroid,
    defined by the spatial first order moments, orientated parallel to
    the principal axes of the power density distribution, and sized
    three times the beam widths".

    This routine creates a mask with `true` values for each pixel in
    the image that should be part of the integration.

    The rectangular mask is `mask_diameters' times the pixel diameters
    of the ellipse.

    The rectangular mask is rotated about (xc, yc) so that it is aligned
    with the elliptical spot.

    Args:
        image: the image to work with
        xc: horizontal center of beam
        yc: vertical center of beam
        d_major: semi-major ellipse diameter
        d_minor: semi-minor ellipse diameter
        phi: angle between horizontal and major axes [radians]
        mask_diameters: number of diameters to include

    Returns:
        masked_image: 2D array with True values inside rectangle
    """
    raw_mask = np.full_like(image, 0, dtype=float)
    v, h = image.shape
    rx = mask_diameters * d_major / 2
    ry = mask_diameters * d_minor / 2
    vlo = max(0, int(yc - ry))
    vhi = min(v, int(yc + ry))
    hlo = max(0, int(xc - rx))
    hhi = min(h, int(xc + rx))

    raw_mask[vlo:vhi, hlo:hhi] = 1
    rot_mask = rotate_image(raw_mask, xc, yc, phi) >= 0.5
    return rot_mask


def rotated_rect_mask(image, xc, yc, d_major, d_minor, phi, mask_diameters=3):
    """
    Create a boolean mask of a rotated rectangle within an image using NumPy.

    Create ISO 11146 rectangular mask for specified beam.

    ISO 11146-2 §7.2 states that integration should be carried out over
    "a rectangular integration area which is centred to the beam centroid,
    defined by the spatial first order moments, orientated parallel to
    the principal axes of the power density distribution, and sized
    three times the beam widths".

    This routine creates a mask with `true` values for each pixel in
    the image that should be part of the integration.

    The rectangular mask is `mask_diameters` times the pixel diameters
    of the ellipse.

    The rectangular mask is rotated about (xc, yc) and then drawn using PIL

    Args:
        image: the image to work with
        xc: horizontal center of beam
        yc: vertical center of beam
        d_major: semi-major ellipse diameter
        d_minor: semi-minor ellipse diameter
        phi: angle between horizontal and major axes [radians]
        mask_diameters: number of diameters to include
    Returns:
        masked_image: 2D array with True values inside rectangle
    """
    height, width = image.shape
    rx = mask_diameters * d_major / 2
    ry = mask_diameters * d_minor / 2

    # create a meshgrid of pixel coordinates
    y, x = np.ogrid[:height, :width]
    x = x - xc
    y = y - yc

    # rotate coordinates by -phi
    cos_phi = np.cos(phi)
    sin_phi = np.sin(phi)
    x_rot = x * cos_phi + y * sin_phi
    y_rot = -x * sin_phi + y * cos_phi

    # define mask for points inside the rotated rectangle
    mask = (np.abs(x_rot) <= rx) & (np.abs(y_rot) <= ry)
    return mask


def iso_background_mask(image, corner_fraction=0.035, nT=3):
    """
    Return a mask indicating the background pixels in an image.

    We estimate the mean and standard deviation using the values in the
    corners.  All pixel values that fall below the mean+nT*stdev are considered
    unilluminated (background) pixels.

    Args:
        image : the image to work with
        nT: how many standard deviations to subtract
        corner_fraction: the fractional size of corner rectangles
    Returns:
        background_mask: 2D array of True/False values
    """
    # estimate background
    ave, std = corner_background(image, corner_fraction=corner_fraction)

    # defined ISO/TR 11146-3:2004, equation 59
    threshold = ave + nT * std

    background_mask = image < threshold

    return background_mask

def subtract_background_image(original, background):
    """
    Subtract a background image from the image with beam.

    The function operates on 2D arrays representing grayscale images. Since the
    subtraction can result in negative pixel values, it is important that the
    return array be an array of float (instead of unsigned arrays that will wrap
    around.

    Args:
        original (numpy.ndarray): 2D array image with beam present.
        background (numpy.ndarray): 2D array image without beam.

    Returns:
        numpy.ndarray: 2D array with background subtracted

    Examples:
        >>> import numpy as np
        >>> original = np.array([[1, 2], [3, 4]])
        >>> background = np.array([[2, 1], [1, 1]])
        >>> subtract_background_image(original, background)
        array([[-1, 1],
               [2, 3]])
    """
    # Checking if the inputs are numpy arrays
    if not isinstance(original, np.ndarray) or not isinstance(background, np.ndarray):
        raise TypeError('Inputs "original" and "background" must be numpy arrays.')

    # Checking if the inputs are two-dimensional arrays
    if original.ndim != 2 or background.ndim != 2:
        raise ValueError('Inputs "original" and "background" must be two-dimensional arrays.')

    # Checking if the shapes of the inputs are equal
    if original.shape != background.shape:
        raise ValueError('Inputs "original" and "background" must have equal shapes.')

    # convert to signed version and subtract
    o = original.astype(float)
    b = background.astype(float)
    subtracted = o - b

    return subtracted


def subtract_constant(original, background, iso_noise=True):
    """
    Return image with a constant value subtracted.

    Subtract threshold from entire image.  If iso_noise is False
    then negative values are set to zero.

    The returned array is an array of float with the shape of original.

    Args:
        original : the image to work with
        background: value to subtract every pixel
        iso_noise: if True then allow negative pixel values
    Returns:
        image: 2D float array with constant background subtracted
    """
    subtracted = original.astype(float)

    if not iso_noise:
        np.place(subtracted, subtracted < background, background)

    subtracted -= background
    return subtracted


def corner_background(image, corner_fraction=0.035):
    """
    Return the mean and stdev of background in corners of image.

    The mean and standard deviation are estimated using the pixels from
    the rectangles in the four corners. The default size of these rectangles
    is 0.035 or 3.5% of the full image size.

    ISO 11146-3 recommends values from 2-5% for `corner_fraction`.

    Args:
        image : the image to work with
        corner_fraction: the fractional size of corner rectangles
    Returns:
        corner_mean: average pixel value in corners
    """
    if corner_fraction == 0:
        return 0, 0
    mask = corner_mask(image, corner_fraction)
    img = np.ma.masked_array(image, ~mask)
    mean = np.mean(img)
    stdev = np.std(img)
    return mean, stdev


def iso_background(image, corner_fraction=0.035, nT=3):
    """
    Return the background for unilluminated pixels in an image.

    This follows one method described in ISO 11146-3 to determine the background
    in an image.

    We first estimate the mean and standard deviation using the values in the
    corners.  All pixel values that fall below the mean+nT*stdev are considered
    un-illuminated (background) pixels.  These are averaged to find the background
    value for the image.

    Args:
        image : the image to work with
        nT: how many standard deviations to subtract
        corner_fraction: the fractional size of corner rectangles
    Returns:
        mean, stdev: mean and stdev of background in the image
    """
    if corner_fraction <= 0 or corner_fraction > 0.25:
        raise ValueError("corner_fraction must be positive and less than 0.25.")

    # estimate background
    ave, std = corner_background(image, corner_fraction=corner_fraction)

    # defined ISO/TR 11146-3:2004, equation 59
    threshold = ave + nT * std

    # collect all pixels that fall below the threshold
    unilluminated = image[image <= threshold]

    if len(unilluminated) == 0:
        raise ValueError("est bkgnd=%.2f stdev=%.2f. No values in image are <= %.2f." % (ave, std, threshold))

    mean = np.mean(unilluminated)
    stdev = np.std(unilluminated)
    return mean, stdev


def _mean_filter(values):
    return np.mean(values)


def _std_filter(values):
    return np.std(values)


def image_background2(image, fraction=0.035, nT=3):
    """
    Return the background of an image.

    The trick here is identifying unilluminated pixels.  This is done by using
    using convolution to find the local average and standard deviation value for
    each pixel.  The local values are done over an n by m rectangle.

    ISO 11146-3 recommends using (n,m) values that are 2-5% of the image

    un-illuminated (background) pixels are all values that fall below the

    Args:
        image : the image to work with
        fraction: the fractional size of corner rectangles
        nT: how many standard deviations to subtract

    Returns:
        background: average background value across image
    """
    # average over a n x m moving kernel
    n, m = (fraction * np.array(image.shape)).astype(int)
    ave = scipy.ndimage.generic_filter(image, _mean_filter, size=(n, m))
    std = scipy.ndimage.generic_filter(image, _std_filter, size=(n, m))

    # defined ISO/TR 11146-3:2004, equation 61
    threshold = ave + nT * std / np.sqrt((n + 1) * (m + 1))

    # we only average the pixels that fall below the illumination threshold
    unilluminated = image[image < threshold]

    background = int(np.mean(unilluminated))
    return background


def subtract_iso_background(image, corner_fraction=0.035, nT=3, iso_noise=True):
    """
    Return image with ISO 11146 background subtracted.

    The mean and standard deviation are estimated using the pixels from
    the rectangles in the four corners. The default size of these rectangles
    is 0.035 or 3.5% of the full image size.

    The new image will have a constant with the corner mean subtracted.

    ISO 11146-3 recommends values from 2-5% for `corner_fraction`.

    ISO 11146-3 recommends from 2-4 for `nT`.

    If iso_noise is False, then after subtracting the mean of the corners,
    pixels values < nT * stdev will be set to zero.

    If iso_noise is True, then no zeroing background is done.

    Args:
        image : the image to work with
        corner_fraction: the fractional size of corner rectangles
        nT: how many standard deviations to subtract
        iso_noise: if True then allow negative pixel values

    Returns:
        image: 2D array with background subtracted
    """
    back, sigma = iso_background(image, corner_fraction=corner_fraction, nT=nT)

    subtracted = image.astype(float)
    subtracted -= back

    if not iso_noise:  # zero pixels that fall within a few stdev
        threshold = nT * sigma
        np.place(subtracted, subtracted < threshold, 0)

    return subtracted


def subtract_corner_background(image, corner_fraction=0.035, nT=3, iso_noise=True):
    """
    Return image with background subtracted.

    The mean and standard deviation are estimated using the pixels from
    the rectangles in the four corners. The default size of these rectangles
    is 0.035 or 3.5% of the full image size.

    The new image will have a constant with the corner mean subtracted.

    ISO 11146-3 recommends values from 2-5% for `corner_fraction`.

    ISO 11146-3 recommends from 2-4 for `nT`.

    If iso_noise is False, then after subtracting the mean of the corners,
    pixels values < nT * stdev will be set to zero.

    If iso_noise is True, then no zeroing background is done.

    Args:
        image : the image to work with
        corner_fraction: the fractional size of corner rectangles
        nT: how many standard deviations to subtract
        iso_noise: if True then allow negative pixel values

    Returns:
        image: 2D array with background subtracted
    """
    back, sigma = corner_background(image, corner_fraction)

    subtracted = image.astype(float)
    subtracted -= back

    if not iso_noise:  # zero pixels that fall within a few stdev
        threshold = nT * sigma
        np.place(subtracted, subtracted < threshold, 0)

    return subtracted


def subtract_tilted_background(image, corner_fraction=0.035):
    """
    Return image with tilted planar background subtracted.

    Take all the points around the perimeter of an image and fit these
    to a tilted plane to determine the background to subtract.  Details of
    the linear algebra are at https://math.stackexchange.com/questions/99299

    Since the sample contains noise, it is important not to remove
    this noise at this stage and therefore we offset the plane so
    that one standard deviation of noise remains.

    Args:
        image : the image to work with
        corner_fraction: the fractional size of corner rectangles
    Returns:
        image: 2D array with tilted planar background subtracted
    """
    v, h = image.shape
    xx, yy = np.meshgrid(range(h), range(v))

    mask = perimeter_mask(image, corner_fraction=corner_fraction)
    perimeter_values = image[mask]
    # coords is (y_value, x_value, 1) for each point in perimeter_values
    coords = np.stack((yy[mask], xx[mask], np.ones(np.size(perimeter_values))), 1)

    # fit a plane to all corner points
    b = np.array(perimeter_values).T
    A = np.array(coords)
    a, b, c = np.linalg.inv(A.T @ A) @ A.T @ b

    # calculate the fitted background plane
    z = a * yy + b * xx + c

    # find the standard deviation of the noise in the perimeter
    # and subtract this value from the plane
    # since we don't want to lose the image noise just yet
    z -= np.std(perimeter_values)

    # finally, subtract the plane from the original image
    return subtract_background_image(image, z)
