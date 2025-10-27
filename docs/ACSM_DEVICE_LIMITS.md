# ACSM Device Limit Issues

## Understanding Errors

When processing ACSM files, you may encounter errors related to device limits imposed by Adobe and Google Books.

### `E_GOOGLE_DEVICE_LIMIT_REACHED`

The `E_GOOGLE_DEVICE_LIMIT_REACHED` error occurs when:

1. **Device Limit**: The Adobe device credentials have been activated on too many devices (Google Books limit: ~6 devices)
2. **Transaction Limit**: The specific ACSM file/transaction has been fulfilled too many times
3. **Expiration**: The ACSM file has expired

#### Solution: Get a Fresh ACSM File

##### Option 1: Download from Google Books (Recommended)

1. Go to [Google Play Books](https://play.google.com/books)
2. Find a free book or one you own
3. Look for the "Download ACSM" option (usually in settings/download options)
4. Save the new `.acsm` file
5. Replace the test file:
   ```bash
   cp /path/to/new/file.acsm assets/test-book.acsm
   ```

##### Option 2: Use a Different Book Source

If Google Books continues to have limits, try:

- [Internet Archive](https://archive.org/) - Many public domain books with ACSM
- [OverDrive](https://www.overdrive.com/) - Library ebooks (requires library card)
- [Adobe Content Server Test Files](https://www.adobe.com/solutions/ebook/digital-editions.html)

### `E_ADEPT_REQUEST_EXPIRED`

The `E_ADEPT_REQUEST_EXPIRED` error indicates the credentials stored in S3 are no longer valid. This will trigger an automatic regeneration of device credentials and retry.

## References

- [Adobe ADEPT Protocol](https://www.adobe.com/solutions/ebook/digital-editions.html)
- [libgourou Documentation](../deps/libgourou/README.md)
- [Knock Lambda Handler](../infrastructure/lambda/handler.py)
