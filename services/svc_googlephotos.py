# This file is part of photoframe (https://github.com/mrworf/photoframe).
#
# photoframe is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# photoframe is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with photoframe.  If not, see <http://www.gnu.org/licenses/>.
#
from base import BaseService
import logging
import re
import json
from urllib2 import urlopen
from urlparse import urljoin

from modules.helper import helper

class GooglePhotos(BaseService):
  SERVICE_NAME = 'Google Photos'
  SERVICE_ID   = 6

  def __init__(self, configDir, id, name):
    BaseService.__init__(self, configDir, id, name, needConfig=False, needOAuth=False)

    self.brokenUrls = []

  def helpKeywords(self):
    return 'Each item is a URL to a public google photos album.'

  def removeKeywords(self, index):
    url = self.getKeywords()[index]
    result = BaseService.removeKeywords(self, index)
    if result and url in self.brokenUrls:
      self.brokenUrls.remove(url)
    return result

  def hasKeywordSourceUrl(self):
    return True

  def getKeywordSourceUrl(self, index):
    keys = self.getKeywords()
    if index < 0 or index >= len(keys):
      return 'Out of range, index = %d' % index
    return keys[index]

  def validateKeywords(self, keywords):
    # Catches most invalid URLs
    if not helper.isValidUrl(keywords):
      return {'error': 'URL appears to be invalid', 'keywords': keywords}

    return BaseService.validateKeywords(self, keywords)

  def memoryForget(self, keywords=None, forgetHistory=False):
    # give broken URLs another try (server may have been temporarily unavailable)
    self.brokenUrls = []
    return BaseService.memoryForget(self, keywords=keywords, forgetHistory=forgetHistory)

  def getUrlFilename(self, url):
    return url.rsplit("/", 1)[-1]

  def selectImageFromAlbum(self, destinationDir, supportedMimeTypes, displaySize, randomize, retry=1):
    result = BaseService.selectImageFromAlbum(self, destinationDir, supportedMimeTypes, displaySize, randomize)
    if result is None:
      return None
    # catch broken urls
    if result.error is not None and result.source is not None:
      logging.warning("broken url detected. You should remove '.../%s' from keywords" % (self.getUrlFilename(result.source)))
    # catch unsupported mimetypes (can only be done after downloading the image)
    elif result.error is None and result.mimetype not in supportedMimeTypes:
      logging.warning("unsupported mimetype '%s'. You should remove '.../%s' from keywords" % (result.mimetype, self.getUrlFilename(result.source)))
    else:
      return result

    # track broken urls / unsupported mimetypes and display warning message on web interface
    self.brokenUrls.append(result.source)
    # retry (with another image)
    if retry > 0:
      return self.selectImageFromAlbum(destinationDir, supportedMimeTypes, displaySize, randomize, retry=retry-1)
    return BaseService.createImageHolder(self).setError('%s uses broken urls / unsupported images!' % self.SERVICE_NAME)

  def getImagesFor(self, keyword):
    url = keyword
    if url in self.brokenUrls:
      return []

    image_data = self.getImageUrls(url)
    images = []

    for img_url, description in image_data:
        image = BaseService.createImageHolder(self) \
            .setId(self.hashString(img_url)) \
            .setUrl(img_url) \
            .setSource(img_url) \
            .allowCache(True) \
            .setDescription(description)
        images.append(image)

    return images

  def getImageUrls(self, url):
    # Fetch the page
    response = urlopen(url)
    html = response.read().decode('utf-8', errors='ignore')
    response.close()

    # Find image sources with regex, capturing src and alt/title
    img_tags = re.findall(r'<img[^>]+>', html, re.IGNORECASE)
    img_urls = []

    for tag in img_tags:
        # Extract src
        src_match = re.search(r'src=["\']?([^"\'>]+)', tag, re.IGNORECASE)
        if not src_match:
            continue
        full_url = urljoin(url, src_match.group(1))
        # Ignore URLs ending with 'p-no'
        if full_url.endswith('p-no'):
            continue
        # Replace the last =something with =w1024-h700-no
        full_url = re.sub(r'=[^=]*$', '=w1024-h700-no', full_url)

        # Check for wrapping <a href="">
        text = ''
        a_match = re.search(r'<a[^>]+href=["\']?([^"\'>]+)[^>]*>' + re.escape(tag), html, re.IGNORECASE)
        if a_match:
            logging.info(urljoin('https://photos.google.com', a_match.group(1)))
            text = self.get_google_photos_description(urljoin('https://photos.google.com', a_match.group(1)))

        img_urls.append((full_url, text))

    return img_urls

  def get_google_photos_description(self, photo_page_url):
    try:
        response = urlopen(photo_page_url)
        html = response.read().decode('utf-8', errors='ignore')
        response.close()

        # Regex to find: "396644657":["Some description text"]
        m = re.search(r'"396644657":\s*\[\s*"([^"]+)"\s*\]', html)
        if m:
            desc = m.group(1).strip()
            logging.info('Found Google Photos description: %s' % desc)
            return desc

        logging.info('No description found for %s' % photo_page_url)
        return ''

    except Exception as e:
        logging.error('Failed to get Google Photos description for %s: %s' % (photo_page_url, e))
        return 'Er ging iets mis met het ophalen van de omschrijving, bel Ruben'

  def getContentUrl(self, image, hints):
    url = image.url
    url = url.replace('{width}', str(hints['size']['width']))
    url = url.replace('{height}', str(hints['size']['height']))
    return url

  # Treat the entire service as one album
  # That way you can group images by creating multiple Simple Url Services
  def nextAlbum(self):
    # Tell the serviceManager to use next service instead
    return False

  def prevAlbum(self):
    # Tell the serviceManager to use previous service instead
    return False

  def resetToLastAlbum(self):
    self.resetIndices()
