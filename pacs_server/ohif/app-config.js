window.config = {
  routerBasename: '/',
  showStudyList: true,
  extensions: [],
  modes: [],
  customizationService: {},
  dataSources: [
    {
      namespace: '@ohif/extension-default.dataSourcesModule.dicomweb',
      sourceName: 'dicomweb',
      configuration: {
        friendlyName: 'Orthanc PACS Server',
        name: 'orthanc',
        // Dùng absolute URL localhost:3001 để browser có thể call qua nginx proxy
        wadoUriRoot: window.location.origin + '/wado',
        qidoRoot: window.location.origin + '/dicom-web',
        wadoRoot: window.location.origin + '/dicom-web',
        qidoSupportsIncludeField: false,
        imageRendering: 'wadors',
        thumbnailRendering: 'wadors',
        enableStudyLazyLoad: true,
        supportsFuzzyMatching: false,
        supportsWildcard: true,
        dicomUploadEnabled: false,
        omitQuotationForMultipartRequest: true,
        // Tắt bulkDataURI để OHIF không follow RetrieveURL internal của Orthanc
        bulkDataURI: {
          enabled: false,
        },
      },
    },
  ],
  defaultDataSourceName: 'dicomweb',
};

