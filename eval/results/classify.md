# Step 5: classification results

68 hand-labelled bullets ({'other': 4, 'breaking': 21, 'fix': 16, 'new': 22, 'deprecated': 5}). Dev = odd ids, test = even ids.
The sample over-represents rare labels, so accuracy is not the corpus-wide accuracy.

| Method | Acc dev | Acc test | Macro-F1 test | Breaking recall test | Breaking precision test | Deprecated recall test |
|---|---|---|---|---|---|---|
| section | 0.65 | 0.56 | 0.47 | 0.33 | 0.67 | 0.00 |
| rules | 0.85 | 0.74 | 0.79 | 0.58 | 0.70 | 1.00 |
| llm | 0.97 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| hybrid | 0.97 | 0.91 | 0.91 | 0.92 | 0.85 | 1.00 |

Hybrid sends 37% of bullets to the LLM (the rest are decided by a keyword rule).

## Errors: rules (14)

| id | gold | pred | section | text |
|---|---|---|---|---|
| c03 | breaking | other | Important Changes Since 3.0.0 | Behavior changes to LoadState: endOfPaginationReached is now always false for LoadType.REFRESH for both PagingSource and RemoteMediator LoadStates from Paging n |
| c05 | new | other | Lifecycle Kotlin Multiplatform Compatibility | lifecycle-runtime moves most APIs to common and supports jvm and iOS in addition to Android. |
| c06 | new | breaking | API Changes | visibleEntries is no longer experimental. (I4829f, b/225394514) |
| c10 | new | breaking | API Changes | Add rememberViewModelStoreProvider to allow creating scoped ViewModelStore instances in Compose. This function links a child store to a parent owner, ensuring V |
| c26 | fix | breaking | Behavior Changes | Main dispatcher is no longer required to run asSnapshot Paging tests. Setting it no longer makes any changes to the test behavior. (Ie56ea) |
| c27 | fix | breaking | Behavior Changes | Navigation Compose's NavHost now sets the graph as part of the first composition. (Ieb7be) |
| c35 | fix | other | Kotlin Multiplatform Compatibility | viewModelScope will fallback to an EmptyCoroutineContext in platforms where Dispatchers.Main is not available (e.g., Linux). |
| c36 | breaking | new | API Changes | All of the default NavType arrays (IntArrayType, LongArrayType, FloatArrayType, BoolArrayType, and StringArrayType) are now of type CollectionNavType (Idcf79, b |
| c42 | breaking | deprecated | New Features | Room now only supports newer Paging APIs (alpha-4+), dropping support for the deprecated LivePagedListProvider. To use the new Room alpha, you’ll need to use pa |
| c50 | breaking | new | API Changes | NavHostController now contains a enableOnBackPressed(boolean) method that replaces the NavHostOnBackPressedManager class that was previously returned by setHost |
| c58 | breaking | other | Important Changes Since 2.9.0 | handleDeepLink was modified to ensure only recognized deep links are handled while all others will be ignored. If this causes an error in your app, consider the |
| c64 | breaking | new | API Changes | Async PagingData Guava-based operators now accept an Executor as a param, to control execution context. (Id4372) |
| c66 | new | other | Important Changes Since 2.6.0 | Kotlin Multiplatform (KMP) Support: In this release, Room has been refactored to become a Kotlin Multiplatform (KMP) library. Current supported platforms are An |
| c67 | other | new | API Changes | All files from the lifecycle-livedata-ktx modules have been moved into the main lifecycle-livedata module. (I10c6f, b/274800183) |

## Errors: llm (1)

| id | gold | pred | section | text |
|---|---|---|---|---|
| c67 | other | breaking | API Changes | All files from the lifecycle-livedata-ktx modules have been moved into the main lifecycle-livedata module. (I10c6f, b/274800183) |

## Errors: hybrid (4)

| id | gold | pred | section | text |
|---|---|---|---|---|
| c06 | new | breaking | API Changes | visibleEntries is no longer experimental. (I4829f, b/225394514) |
| c10 | new | breaking | API Changes | Add rememberViewModelStoreProvider to allow creating scoped ViewModelStore instances in Compose. This function links a child store to a parent owner, ensuring V |
| c42 | breaking | deprecated | New Features | Room now only supports newer Paging APIs (alpha-4+), dropping support for the deprecated LivePagedListProvider. To use the new Room alpha, you’ll need to use pa |
| c67 | other | breaking | API Changes | All files from the lifecycle-livedata-ktx modules have been moved into the main lifecycle-livedata module. (I10c6f, b/274800183) |
