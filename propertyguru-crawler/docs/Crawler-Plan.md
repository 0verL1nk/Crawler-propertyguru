# 爬取网站propertyguru的所有房产资料
> 基本Url: https://www.propertyguru.com.sg/property-for-sale/1,最大页数可以找ul da-id="hui-pagination"下的的倒数第三个li class="pageitem"
> 需要注意的是,这些房产更新比较频繁,需要注意爬取的逻辑,
## 流程
> 注意使用browserAPI
1. 首先访问基本Url(比如第一页),主要内容在div class="search-result-root"下的每一个div,姑且称为房产div,其属性da-id="parent-listing-card-v2-regular",然后另一个属性da-listing-id为其uniqueID,到时候存入数据库要记得根据此来去重
2. 遍历每个房产div,其内部有个a class="card-footer",href为详情页面,我们后面还需要进入详情界面抓取数据,目前在这个a下有一些基本信息,
```html
<div class="details-group-section"><div class="price-section"><div class="listing-price-availability"><div class="listing-price" da-id="listing-card-v2-price">S$ 708,000</div><p class="hui-typography pg-font-body-xs listing-ppa" da-id="listing-card-v2-psf">S$ 707.29 psf</p></div></div><div class="content"><div class="title-location"><div class="title-badge-wrapper"><h3 class="hui-typography pg-font-label-m listing-type-text" da-id="listing-card-v2-title">619D Punggol Drive</h3></div><p class="hui-typography pg-font-body-xs listing-address">619D Punggol Drive</p></div><div class="listing-feature-group my-2 flex-wrap align-items-stretch hstack gap-2"><div da-id="listing-card-v2-bedrooms" class="info-item d-flex hstack gap-1"><div class="hui-svgicon hui-svgicon--bed-o hui-svgicon--s" da-id="svg-icon" style="background-color: var(--icon-active-secondary);"></div><p class="hui-typography pg-font-body-xs">3</p></div><div da-id="listing-card-v2-bathrooms" class="info-item d-flex hstack gap-1"><div class="hui-svgicon hui-svgicon--bath-o hui-svgicon--s" da-id="svg-icon" style="background-color: var(--icon-active-secondary);"></div><p class="hui-typography pg-font-body-xs">2</p></div><span class="vertical-line"></span><div da-id="listing-card-v2-area" class="info-item d-flex hstack gap-1"><p class="hui-typography pg-font-body-xs">1,001 sqft</p></div><span class="vertical-line"></span><div da-id="listing-card-v2-unit-type" class="info-item d-flex hstack gap-1"><p class="hui-typography pg-font-body-xs">HDB Flat</p></div><span class="vertical-line"></span><div da-id="listing-card-v2-tenure" class="info-item d-flex hstack gap-1"><p class="hui-typography pg-font-body-xs">99-year Leasehold</p></div><span class="vertical-line"></span><div da-id="listing-card-v2-build-year" class="info-item d-flex hstack gap-1"><p class="hui-typography pg-font-body-xs">Built: 2012</p></div></div><div class="listing-location" da-id="listing-card-v2-mrt"><div class="color-badge-root mrt-color-badge" style="background: linear-gradient(90deg, rgb(115, 131, 118) 0%, rgb(115, 131, 118) 100%);"></div><span class="listing-location-value">3 min (260 m) from PE6 Oasis LRT Station</span></div><ul class="listing-recency" da-id="listing-card-v2-recency"><div class="info-item d-flex hstack gap-1"><div class="hui-svgicon hui-svgicon--clock-circle-o hui-svgicon--s" da-id="svg-icon" style="background-color: var(--icon-active-secondary);"></div><span class="hui-typography pg-font-caption-xs">Listed on Nov 03, 2025 (18m ago)</span></div></ul></div></div>
```
3. 进入详情页,就是我们刚才看到的a的href,进入,一步步看
a. 首先是`Property details`
```html
<div class="meta-table-root" da-id="property-details"><div class="row"><h2 da-id="metatable-title" class="meta-table__title col">Property details</h2></div><table class="row"><tbody><tr class="row"><td class="meta-table__item-wrapper col-md-6 col-12"><div class="meta-table__item"><div class="row"><div class="meta-table__item__wrapper"><img loading="eager" src="https://cdn.pgimgs.com/hive-ui-core/static/v1.6/icons/svgs/home-open-o.svg" alt="home-open-o" class="hui-svgicon hui-svgicon--m meta-table__item__wrapper__icon" height="24" width="24" aria-label="home-open-o" da-id="svg-icon" draggable="false"><div class="meta-table__item__wrapper__value" da-id="metatable-item">Condominium for sale</div></div></div></div></td><td class="meta-table__item-wrapper col-md-6 col-12"><div class="meta-table__item"><div class="row"><div class="meta-table__item__wrapper"><img loading="eager" src="https://cdn.pgimgs.com/hive-ui-core/static/v1.6/icons/svgs/furnished-o.svg" alt="furnished-o" class="hui-svgicon hui-svgicon--m meta-table__item__wrapper__icon" height="24" width="24" aria-label="furnished-o" da-id="svg-icon" draggable="false"><div class="meta-table__item__wrapper__value" da-id="metatable-item">Partially furnished</div></div></div></div></td></tr><tr class="row"><td class="meta-table__item-wrapper col-md-6 col-12"><div class="meta-table__item"><div class="row"><div class="meta-table__item__wrapper"><img loading="eager" src="https://cdn.pgimgs.com/hive-ui-core/static/v1.6/icons/svgs/document-with-lines-o.svg" alt="document-with-lines-o" class="hui-svgicon hui-svgicon--m meta-table__item__wrapper__icon" height="24" width="24" aria-label="document-with-lines-o" da-id="svg-icon" draggable="false"><div class="meta-table__item__wrapper__value" da-id="metatable-item">TOP in Dec 2022</div></div></div></div></td><td class="meta-table__item-wrapper col-md-6 col-12"><div class="meta-table__item"><div class="row"><div class="meta-table__item__wrapper"><img loading="eager" src="https://cdn.pgimgs.com/hive-ui-core/static/v1.6/icons/svgs/calendar-days-o.svg" alt="calendar-days-o" class="hui-svgicon hui-svgicon--m meta-table__item__wrapper__icon" height="24" width="24" aria-label="calendar-days-o" da-id="svg-icon" draggable="false"><div class="meta-table__item__wrapper__value" da-id="metatable-item">99-year lease</div></div></div></div></td></tr><tr class="row"><td class="meta-table__item-wrapper col-md-6 col-12"><div class="meta-table__item"><div class="row"><div class="meta-table__item__wrapper"><img loading="eager" src="https://cdn.pgimgs.com/hive-ui-core/static/v1.6/icons/svgs/calendar-time-o.svg" alt="calendar-time-o" class="hui-svgicon hui-svgicon--m meta-table__item__wrapper__icon" height="24" width="24" aria-label="calendar-time-o" da-id="svg-icon" draggable="false"><div class="meta-table__item__wrapper__value" da-id="metatable-item">Listed on 3 Nov 2025</div></div></div></div></td><td class="meta-table__item-wrapper col-md-6 col-12"><div class="meta-table__item"><div class="row"><div class="meta-table__item__wrapper"><img loading="eager" src="https://cdn.pgimgs.com/hive-ui-core/static/v1.6/icons/svgs/document-with-lines-o.svg" alt="document-with-lines-o" class="hui-svgicon hui-svgicon--m meta-table__item__wrapper__icon" height="24" width="24" aria-label="document-with-lines-o" da-id="svg-icon" draggable="false"><div class="meta-table__item__wrapper__value" da-id="metatable-item">Listing ID - 60180605</div></div></div></div></td></tr></tbody></table><button type="button" da-id="meta-table-see-more-btn" class="meta-table__button btn btn-secondary btn-sm">See all details</button></div>
```

b. 然后是`About this property`
```html
<div class="description-block-root" da-id="description-widget"><h2 class="title">About this property</h2><h3 class="subtitle">Impeccable, airy unit with unblocked views, move-in ready, no west sun</h3><div class="description trimmed">Call Rosie Lee 8939*0880 ❤️ to arrange for an exclusive viewing now.<br><br><br><br>WhatsApp for photos and floor plan ❤️ Rosie Lee 8939*0880<br><br><br><br>Almost brand new! <br><br>Move-In Ready 2 Bed, 2 Bath Premium – Best Unit Available! <br><br>	•	Bright &amp; Breezy: Impeccable unit with unblocked views, no west sun<br><br>	•	Location: Sixth Ave MRT at doorstep with covered walkway<br><br>	•	Schools Nearby: Raffles Girls’ Primary within 1 km<br><br>	•	Facilities: Full condo facilities including tennis court, 50m lap pool, gym, and more<br><br>	•	Convenience: Easy access to amenities and transport<br><br>Interested? Chat with me Rosie Lee on WhatsApp ❤️ 8939*0880</div><button type="button" da-id="description-widget-show-more-lnk" class="hui-button read-more btn btn-secondary btn-sm"><div class="btn-content">See more</div></button></div>
```
同样注意,如果有button,需要点击,才有详细信息,我们需要收集详细信息,以下是点击按钮后才出现的内容

c. 其次是`Amenities`
```html
<div class="property-amenities-root" da-id="property-amenities"><h5 class="hui-typography pg-font-title-xs property-amenities__title" da-id="facilities-amenities-title">Amenities</h5><div class="property-amenities__tab-header-item"><div class="property-amenities__body"><div class="property-amenities__row row"><div class="col-md-6 col-12"><div class="property-amenities__row-item" da-id="facilities-amenities-data"><img loading="eager" src="https://cdn.pgimgs.com/hive-ui-core/static/v1.6/icons/svgs/aircon-o.svg" alt="aircon-o" class="hui-svgicon hui-svgicon--m property-amenities__row-item__icon" height="24" width="24" aria-label="aircon-o" da-id="svg-icon" draggable="false"><p class="hui-typography pg-font-body-s property-amenities__row-item__value">Air conditioner</p></div></div><div class="col-md-6 col-12"><div class="property-amenities__row-item" da-id="facilities-amenities-data"><img loading="eager" src="https://cdn.pgimgs.com/hive-ui-core/static/v1.6/icons/svgs/balcony-o.svg" alt="balcony-o" class="hui-svgicon hui-svgicon--m property-amenities__row-item__icon" height="24" width="24" aria-label="balcony-o" da-id="svg-icon" draggable="false"><p class="hui-typography pg-font-body-s property-amenities__row-item__value">Balcony</p></div></div></div><div class="property-amenities__row row"><div class="col-md-6 col-12"><div class="property-amenities__row-item" da-id="facilities-amenities-data"><img loading="eager" src="https://cdn.pgimgs.com/hive-ui-core/static/v1.6/icons/svgs/light-bulb-simple-o.svg" alt="light-bulb-simple-o" class="hui-svgicon hui-svgicon--m property-amenities__row-item__icon" height="24" width="24" aria-label="light-bulb-simple-o" da-id="svg-icon" draggable="false"><p class="hui-typography pg-font-body-s property-amenities__row-item__value">Basic lights</p></div></div><div class="col-md-6 col-12"><div class="property-amenities__row-item" da-id="facilities-amenities-data"><img loading="eager" src="https://cdn.pgimgs.com/hive-ui-core/static/v1.6/icons/svgs/walk-in-wardrobe-o.svg" alt="walk-in-wardrobe-o" class="hui-svgicon hui-svgicon--m property-amenities__row-item__icon" height="24" width="24" aria-label="walk-in-wardrobe-o" da-id="svg-icon" draggable="false"><p class="hui-typography pg-font-body-s property-amenities__row-item__value">Cabinets</p></div></div></div></div></div><button type="button" da-id="amenities-see-all-btn" class="hui-button amenities-button btn btn-secondary btn-sm"><div class="btn-content"><span class="hui-typography pg-font-label-s">See all 13 amenities</span></div></button></div>
```

d. 然后是`Common facilities`
```html
<div class="property-amenities-root" da-id="property-facilities"><h5 class="hui-typography pg-font-title-xs property-amenities__title" da-id="facilities-amenities-title">Common facilities</h5><div class="property-amenities__tab-header-item"><div class="property-amenities__body"><div class="property-amenities__row row"><div class="col-md-6 col-12"><div class="property-amenities__row-item" da-id="facilities-amenities-data"><img loading="eager" src="https://cdn.pgimgs.com/hive-ui-core/static/v1.6/icons/svgs/security-access-control-o.svg" alt="security-access-control-o" class="hui-svgicon hui-svgicon--m property-amenities__row-item__icon" height="24" width="24" aria-label="security-access-control-o" da-id="svg-icon" draggable="false"><p class="hui-typography pg-font-body-s property-amenities__row-item__value">24 hours security</p></div></div><div class="col-md-6 col-12"><div class="property-amenities__row-item" da-id="facilities-amenities-data"><img loading="eager" src="https://cdn.pgimgs.com/hive-ui-core/static/v1.6/icons/svgs/bbq-o.svg" alt="bbq-o" class="hui-svgicon hui-svgicon--m property-amenities__row-item__icon" height="24" width="24" aria-label="bbq-o" da-id="svg-icon" draggable="false"><p class="hui-typography pg-font-body-s property-amenities__row-item__value">Barbeque pits</p></div></div></div><div class="property-amenities__row row"><div class="col-md-6 col-12"><div class="property-amenities__row-item" da-id="facilities-amenities-data"><img loading="eager" src="https://cdn.pgimgs.com/hive-ui-core/static/v1.6/icons/svgs/parking-o.svg" alt="parking-o" class="hui-svgicon hui-svgicon--m property-amenities__row-item__icon" height="24" width="24" aria-label="parking-o" da-id="svg-icon" draggable="false"><p class="hui-typography pg-font-body-s property-amenities__row-item__value">Basement car park</p></div></div><div class="col-md-6 col-12"><div class="property-amenities__row-item" da-id="facilities-amenities-data"><img loading="eager" src="https://cdn.pgimgs.com/hive-ui-core/static/v1.6/icons/svgs/parking-o.svg" alt="parking-o" class="hui-svgicon hui-svgicon--m property-amenities__row-item__icon" height="24" width="24" aria-label="parking-o" da-id="svg-icon" draggable="false"><p class="hui-typography pg-font-body-s property-amenities__row-item__value">Car park</p></div></div></div></div></div><button type="button" da-id="facilities-see-all-btn" class="hui-button amenities-button btn btn-secondary btn-sm"><div class="btn-content"><span class="hui-typography pg-font-label-s">See all 7 facilities</span></div></button></div>
```


1. 接下来是房产的图片
```html
<div class="media-gallery-image-grid"><a href="#" class="hui-buttonlink image-container media-gallery-image-grid-col-2 media-gallery-image-grid-row-2"><img class="hui-image hui-image--1_1 media-image images" src="https://sg1-cdn.pgimgs.com/listing/60180605/UPHO.157281007.V800/Fourth-Avenue-Residences-Tanglin-Holland-Bukit-Timah-Singapore.jpg" alt="Living room " da-id="media-gallery-images" fetchpriority="high"></a><a href="#" class="hui-buttonlink image-container"><img class="hui-image hui-image--1_1 media-image floorPlans" src="https://sg1-cdn.pgimgs.com/projectnet-unit/213784/ZUFP.150455249.V800.jpg" alt="Image" da-id="media-gallery-floorPlans" fetchpriority="high"></a><a href="#" class="hui-buttonlink image-container"><img class="hui-image hui-image--1_1 media-image images" src="https://sg1-cdn.pgimgs.com/listing/60180605/UPHO.157281025.V800/Fourth-Avenue-Residences-Tanglin-Holland-Bukit-Timah-Singapore.jpg" alt="Living room " da-id="media-gallery-images" fetchpriority="high"></a><a href="#" class="hui-buttonlink image-container"><img class="hui-image hui-image--1_1 media-image images" src="https://sg1-cdn.pgimgs.com/listing/60180605/UPHO.157281022.V800/Fourth-Avenue-Residences-Tanglin-Holland-Bukit-Timah-Singapore.jpg" alt="Bedroom" da-id="media-gallery-images" fetchpriority="high"></a><a href="#" class="hui-buttonlink image-container"><img class="hui-image hui-image--1_1 media-image images" src="https://sg1-cdn.pgimgs.com/listing/60180605/UPHO.157281023.V800/Fourth-Avenue-Residences-Tanglin-Holland-Bukit-Timah-Singapore.jpg" alt="Master Bedroom" da-id="media-gallery-images" fetchpriority="high"></a></div>
```

不需要视频
## 最简单方式!!

另外,我有重大发现,实际上,详情页所有数据都在<script id="__NEXT_DATA__" type="application/json" nonce="" crossorigin="anonymous">下,为json格式,一些数据定位如下:
- 图片: props.PageProps.pageData.data.mediaExplorerData.mediaGroups.images.items,为列表,如下所示
```
"items": [
    {
        "src": "https://sg1-cdn.pgimgs.com/listing/60046991/UPHO.155769836.V800/Pasir-Ris-8-Pasir-Ris-Tampines-Singapore.jpg",
        "caption": "Living Room"
    },
    {
        "src": "https://sg1-cdn.pgimgs.com/listing/60046991/UPHO.155769837.V800/Pasir-Ris-8-Pasir-Ris-Tampines-Singapore.jpg",
        "caption": "Living Room"
    },
]
```
- Property details: props.PageProps.pageData.data.detailsData.metatable.items,也是列表,如下所示,我们只需要value
```
[
    {
        "icon": "home-open-o",
        "value": "Condominium for sale"
    },
    {
        "icon": "furnished-o",
        "value": "Partially furnished"
    }
]
```
- About this property: props.PageProps.pageData.data.descriptionBlockData,是一个字典,其中有几个内容
  - title
  - subtitle
  - description
- Amenities: props.PageProps.pageData.data.amenitiesData.data,也是列表,如下所示,我们只需要text:
```
[
    {
        "icon": "walk-in-wardrobe-o",
        "text": "Cabinets"
    },
    {
        "icon": "asterisk-o",
        "text": "Fridge"
    },
]
```
- Common facilities: props.PageProps.pageData.data.facilitiesData.data,也是列表,内容如下,我们只需要text:
```
[
    {
        "icon": "security-access-control-o",
        "text": "24 hours security"
    },
    {
        "icon": "outdoor-gym-o",
        "text": "Adult fitness stations"
    },
]
```